"""Targeted A08 regressions. No key, network or full private transcript fixtures."""
import copy
import json
import unittest
import httpx
from backend.app.dashboard.customer_actor import (
    ActorContractError, actor_context, actor_schema, verifier_schema,
    validate_actor, validate_review,
)
from backend.app.dashboard.response_planning import build_response_plan, normalize_targets
from backend.app.dashboard.engine import process_turn
from backend.app.dashboard.providers import OpenAIProvider, ProviderError
from test_engine import new_session, decision, response_body, FixedProvider
from test_response_planning import candidate, review, planned_context


def statement_context(text='Мы готовы починить вашу печь', intent='premature_offer'):
    session=new_session(2,mode='openai')
    d={**decision(act='other' if intent in {'clarify','discuss_price'} else 'proposal',source_quote=text), 'question_targets':[]}
    context={'language':'ru','customer_name':session['scenario_snapshot']['customer_name'],
             'opening':session['scenario_snapshot']['opening'],'learner_text':text,
             'visible_history':session['messages'],'response_intent':intent,
             'authorized_facts':[],'must_address_fact_ids':[]}
    context['response_plan']=build_response_plan(session,d,text,intent,[])
    return actor_context(context)


class SevenFailureContractRegressions(unittest.TestCase):
    def test_case_1_3_compound_type_identification_and_unknown_date_remain_distinct(self):
        s=new_session(2,mode='openai');text='Какая у вас печь, каковы её номер и мощность, когда был последний технический осмотр?'
        d={**decision(act='question',fact_ids=['identification'],source_quote=text),
           'question_targets':[{'target':'equipment_identification','quote':'каковы её номер и мощность','fact_ids':['identification']},
                               {'target':'maintenance_history','quote':'когда был последний технический осмотр','fact_ids':[]}]}
        facts={f['id']:f for f in s['scenario_snapshot']['facts']}
        targets=normalize_targets(d,text,facts)
        self.assertEqual({t['target'] for t in targets},{'equipment_need','equipment_identification','maintenance_history'})
        self.assertEqual(next(t['fact_ids'] for t in targets if t['target']=='equipment_need'),['goal'])
        self.assertEqual(next(t['fact_ids'] for t in targets if t['target']=='maintenance_history'),[])

    def test_case_1_3_unknown_target_can_be_covered_but_all_true_without_coverage_is_rejected(self):
        c=planned_context();text='Дату последнего техосмотра сейчас подтвердить не могу.'
        self.assertEqual(validate_review(review(c),c,text),[])
        with self.assertRaises(ActorContractError) as e:
            validate_review(review(c,addressed_targets=[]),c,text)
        self.assertEqual(e.exception.code,'ai_actor_wrong_target')

    def test_case_1_7_actor_empty_targets_schema_excludes_own_followup_question_ids(self):
        c=statement_context();schema=actor_schema(c)['properties']['addressed_targets']
        self.assertEqual(schema['maxItems'],0)
        bad=candidate(c,'Прежде чем соглашаться, хочу уточнить ваш опыт.');bad['addressed_targets']=['company_services']
        with self.assertRaises(ActorContractError):validate_actor(bad,c)

    def test_case_1_8_acknowledging_tuesday_without_booking_is_valid(self):
        c=statement_context('Давайте запишем мастера на вторник')
        text='Спасибо за предложение. Прежде чем назначать вторник, уточните, сможете ли вы обслужить моё оборудование?'
        self.assertEqual(validate_actor(candidate(c,text),c),text)
        self.assertEqual(validate_review(review(c),c,text),[])

    def test_case_2_5_verifier_empty_targets_schema_excludes_fact_ids(self):
        c=statement_context('Мы как раз такая компания, ремонтируем такие печи.','clarify')
        self.assertEqual(verifier_schema(c)['properties']['addressed_targets']['maxItems'],0)
        with self.assertRaises(ActorContractError):
            validate_review(review(c,addressed_targets=['cause']),c,'Вы действительно работаете с такими печами?')

    def test_case_2_7_natural_repair_hesitation_is_not_consent(self):
        c=statement_context('Мы готовы её починить');text='Сначала хотелось бы понять, подходит ли ваша специализация для моей печи.'
        self.assertEqual(validate_review(review(c),c,text),[])

    def test_case_2_8_visit_hesitation_is_accepted_and_no_extra_targets_appear(self):
        c=statement_context('Предлагаю записать вас на визит мастера во вторник')
        text='Пока не будем назначать визит. Вы сможете сначала уточнить, подходит ли вам моё оборудование?'
        self.assertEqual(validate_review(review(c),c,text),[])
        self.assertEqual(c['response_plan']['question_targets'],[])

    def test_case_2_9_generic_experience_reply_is_rejected_even_with_all_true_review(self):
        c=statement_context('Я думаю, ремонт будет стоить 15 000 евро','discuss_price')
        with self.assertRaises(ActorContractError) as e:
            validate_review(review(c),c,'Расскажите о вашем опыте диагностики и гарантийном сроке ремонта.')
        self.assertEqual(e.exception.code,'ai_actor_wrong_target')
        self.assertEqual(validate_review(review(c),c,'Откуда взялась эта сумма? На чём основан расчёт?'),[])

    def test_critical_unsupported_commitments_stay_blocked_despite_positive_verifier(self):
        c=statement_context()
        for text in ['Запишите меня на вторник.','Я согласен на ремонт.','Цена меня устраивает.']:
            with self.subTest(reply=text),self.assertRaises(ActorContractError):validate_review(review(c),c,text)

    def test_normal_russian_german_and_attributed_speech_stay_valid(self):
        c=statement_context()
        for text in ['А вы можете помочь с печью?','Können Sie einen Techniker schicken?',
                     'Не записывайте меня на вторник.','Спасибо, сначала уточним условия.',
                     'Вы сказали: «Запишите меня на вторник». Я не подтверждал такую запись.']:
            with self.subTest(reply=text):validate_review(review(c),c,text)

    def test_receiver_role_inversion_is_blocked_but_sending_technician_question_is_valid(self):
        c=statement_context()
        with self.assertRaises(ActorContractError):validate_review(review(c),c,'Когда вы можете принять мастера?')
        self.assertEqual(validate_review(review(c),c,'Когда вы можете прислать мастера?'),[])

    def test_unprovided_date_is_not_personal_ignorance_but_authored_unknown_can_be(self):
        c=planned_context()
        with self.assertRaises(ActorContractError):validate_review(review(c),c,'Я не помню дату последнего осмотра.')
        self.assertEqual(validate_review(review(c),c,'Дату последнего осмотра сейчас назвать не могу.'),[])
        # Unknown identification in the same sentence does not become unknown inspection.
        self.assertEqual(validate_review(review(c),c,'Модель не помню, а дату осмотра сейчас подтвердить не могу.'),[])

    def test_service_withdrawal_does_not_become_closed_company(self):
        c=planned_context('service_change_reason',['reason'],'Почему к нам?')
        with self.assertRaises(ActorContractError):validate_review(review(c),c,'Фирма закрылась и ушла из города.')
        self.assertEqual(validate_review(review(c),c,'Фирма прекратила обслуживание в нашем городе.'),['reason'])


class ReliabilityPipelineRegressions(unittest.IsolatedAsyncioTestCase):
    async def test_price_claim_gets_specific_reaction_without_state_progress(self):
        session=new_session(2,mode='openai');seen=[]
        class P(FixedProvider):
            async def respond(self,c):
                seen.append(c)
                return {'reply':'На чём основана эта сумма без оценки специалиста?','verified_fact_ids':[]}
        text='Ремонт стоит примерно 15 000 евро'
        result=await process_turn(session,text,'message',P(decision(act='other',source_quote=text)),1)
        self.assertEqual(seen[0]['response_intent'],'discuss_price')
        self.assertEqual(result['state']['phase'],'needs');self.assertIsNone(result['state']['outcome'])
        self.assertNotIn('clarification_requested',[e['type'] for e in result['state']['events']])

    async def test_question_button_kind_does_not_override_actual_proposal_and_incompatibility_stays_blocked(self):
        session=new_session(2,mode='openai')
        session['state'].update(phase='proposal',needs_confirmed=True,capabilities_confirmed=True,
            discovered=[f['id'] for f in session['scenario_snapshot']['facts']])
        class P(FixedProvider):
            async def respond(self,c):
                return {'reply':'Как вы сможете помочь, если такое оборудование вам не подходит?','verified_fact_ids':[]}
        text='Мы готовы починить вашу печь'
        result=await process_turn(session,text,'message',P(decision(act='proposal',source_quote=text,
            proposal_outcome='repair',proposal_ok=True)),1)
        self.assertIsNone(result['state']['outcome'])
        self.assertEqual(result['state']['events'][-1]['type'],'proposal_not_grounded')
        self.assertNotEqual(result['state']['phase'],'completed')

    async def test_retry_feedback_names_exact_target_set_without_approving_bad_reply(self):
        c=statement_context();requests=[]
        bad=candidate(c,'Вы сможете помочь?');bad['addressed_targets']=['company_services']
        outputs=[bad,candidate(c,'Сначала уточним, сможете ли вы помочь.'),review(c)]
        async def handler(request):
            requests.append(json.loads(request.content));return httpx.Response(200,json=response_body(outputs[len(requests)-1]))
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            p=OpenAIProvider('fake','model',client=client);await p.respond(c)
        feedback=json.loads(requests[1]['input'][1]['content'])['generation_feedback']
        self.assertEqual(feedback['valid_target_ids'],[]);self.assertEqual(p.request_count,3)
        rejected=next(t for t in p.trace if t['kind']=='validation' and not t['accepted'])
        self.assertEqual(rejected['rejection_stage'],'local_actor')

    async def test_usage_counters_are_recorded_without_raw_response_or_key(self):
        calls=[]
        async def handler(request):
            calls.append(request);body=response_body(decision())
            body['usage']={'input_tokens':100,'input_tokens_details':{'cached_tokens':40},'output_tokens':20}
            return httpx.Response(200,json=body)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            p=OpenAIProvider('never-output-this-synthetic-secret','model',client=client)
            await p.interpret(new_session(2,mode='openai'),'Здравствуйте','message')
        usage=next(t for t in p.trace if t['kind']=='usage')
        self.assertEqual((usage['input_tokens'],usage['cached_input_tokens'],usage['output_tokens']),(100,40,20))
        self.assertNotIn('never-output-this-synthetic-secret',json.dumps(p.trace))


class FollowupObservedFailures(unittest.TestCase):
    def test_indirect_price_report_keeps_customer_ownership(self):
        c=statement_context('Ремонт стоит 15 000 евро','discuss_price')
        with self.assertRaises(ActorContractError) as error:
            validate_review(review(c),c,'Вы упомянули, что ремонт вашей печи стоит 15 000 евро. Откуда эта сумма?')
        self.assertEqual(error.exception.check,'indirect_speech_keeps_customer_equipment')
        for text in ['Вы сказали, что ремонт моей печи стоит 15 000 евро. Как это рассчитано?',
                     'Вы сказали: «Ремонт вашей печи стоит 15 000 евро». Откуда эта сумма?']:
            with self.subTest(reply=text):self.assertEqual(validate_review(review(c),c,text),[])

    def test_stale_history_questions_cannot_authorize_facts_for_current_proposal(self):
        text='Мы обслуживаем только электрические печи. Давайте починим вашу газовую печь?'
        d={**decision(act='proposal',source_quote=text), 'question_targets':[
            {'target':'fault_cause','quote':'Как вы определяете причину неисправности?','fact_ids':['cause']}]}
        facts={f['id']:f for f in new_session(2)['scenario_snapshot']['facts']}
        self.assertEqual(normalize_targets(d,text,facts),[])
        self.assertEqual(d['fact_ids'],[])
        # Do not silently forgive out-of-turn evidence on genuine questions.
        d['act']='question'
        with self.assertRaises(ValueError):normalize_targets(d,text,facts)
