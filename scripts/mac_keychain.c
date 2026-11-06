/* Narrow macOS Keychain bridge. Secrets use anonymous pipes, never argv. */
#include <Security/Security.h>
#include <CoreFoundation/CoreFoundation.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <stdlib.h>

static void wipe(volatile unsigned char *p, size_t n) { while (n--) *p++ = 0; }
static int status_exit(OSStatus status) {
    if (status == errSecSuccess) return 0;
    fprintf(stderr, "KEYCHAIN_STATUS_%d\n", (int)status);
    return status == errSecItemNotFound ? 44 : 1;
}
int main(int argc, char **argv) {
    if (argc < 2) return 64;
    const char *service = argc > 2 ? argv[2] : "pro.klareki.beratungstrainer.openai";
    CFStringRef name = CFStringCreateWithCString(NULL, service, kCFStringEncodingUTF8);
    if (!name) return 65;
    CFMutableDictionaryRef query = CFDictionaryCreateMutable(NULL, 0,
        &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
    CFDictionarySetValue(query, kSecClass, kSecClassGenericPassword);
    CFDictionarySetValue(query, kSecAttrService, name);
    CFDictionarySetValue(query, kSecAttrAccount, CFSTR("default"));
    OSStatus status = errSecParam;
    if (!strcmp(argv[1], "get")) {
        if (isatty(STDOUT_FILENO)) { CFRelease(query); CFRelease(name); return 64; }
        CFDictionarySetValue(query, kSecReturnData, kCFBooleanTrue);
        CFDictionarySetValue(query, kSecMatchLimit, kSecMatchLimitOne);
        CFTypeRef result = NULL;
        status = SecItemCopyMatching(query, &result);
        if (status == errSecSuccess) {
            if (!result || CFGetTypeID(result) != CFDataGetTypeID()) status = errSecDecode;
            else fwrite(CFDataGetBytePtr((CFDataRef)result), 1,
                        (size_t)CFDataGetLength((CFDataRef)result), stdout);
        }
        if (result) CFRelease(result);
    } else if (!strcmp(argv[1], "set")) {
        if (isatty(STDIN_FILENO)) { CFRelease(query); CFRelease(name); return 64; }
        unsigned char secret[8193];
        size_t length = fread(secret, 1, sizeof(secret), stdin);
        if (!length || length > 8192) { wipe(secret, sizeof(secret)); return 65; }
        CFDataRef data = CFDataCreate(NULL, secret, (CFIndex)length);
        wipe(secret, sizeof(secret));
        const void *keys[] = { kSecValueData };
        const void *values[] = { data };
        CFDictionaryRef changed = CFDictionaryCreate(NULL, keys, values, 1,
            &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
        status = SecItemUpdate(query, changed);
        if (status == errSecItemNotFound) {
            CFDictionarySetValue(query, kSecValueData, data);
            CFDictionarySetValue(query, kSecAttrAccessible, kSecAttrAccessibleWhenUnlockedThisDeviceOnly);
            status = SecItemAdd(query, NULL);
        }
        CFRelease(changed); CFRelease(data);
    } else if (!strcmp(argv[1], "delete")) {
        status = SecItemDelete(query);
        if (status == errSecItemNotFound) status = errSecSuccess;
    }
    CFRelease(query); CFRelease(name);
    return status_exit(status);
}
