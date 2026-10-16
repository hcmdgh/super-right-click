#import <Cocoa/Cocoa.h>

// Escape the AppleScript literal. The script then uses `quoted form of` to
// escape the same path for the shell; these are two distinct quoting layers.
static NSString *AppleScriptString(NSString *value) {
    NSString *escaped = [value stringByReplacingOccurrencesOfString:@"\\" withString:@"\\\\"];
    escaped = [escaped stringByReplacingOccurrencesOfString:@"\"" withString:@"\\\""];
    escaped = [escaped stringByReplacingOccurrencesOfString:@"\r" withString:@"\\r"];
    escaped = [escaped stringByReplacingOccurrencesOfString:@"\n" withString:@"\\n"];
    return [NSString stringWithFormat:@"\"%@\"", escaped];
}

@interface ITermMenuDelegate : NSObject <NSApplicationDelegate>
@end

@implementation ITermMenuDelegate
- (void)applicationWillFinishLaunching:(NSNotification *)notification {
    (void)notification;
    [[NSAppleEventManager sharedAppleEventManager] setEventHandler:self
        andSelector:@selector(handleGetURL:reply:)
        forEventClass:kInternetEventClass andEventID:kAEGetURL];
}

- (void)handleGetURL:(NSAppleEventDescriptor *)event reply:(NSAppleEventDescriptor *)reply {
    (void)reply;
    NSString *value = [[event paramDescriptorForKeyword:keyDirectObject] stringValue];
    NSURL *url = value ? [NSURL URLWithString:value] : nil;
    if (url) [self application:NSApp openURLs:@[url]];
}

- (void)application:(NSApplication *)application openURLs:(NSArray<NSURL *> *)urls {
    (void)application;
    for (NSURL *url in urls) {
        if (![url.scheme isEqualToString:@"genghao-open-iterm"] ||
            ![url.host isEqualToString:@"open"]) continue;
        NSURLComponents *components = [NSURLComponents componentsWithURL:url resolvingAgainstBaseURL:NO];
        for (NSURLQueryItem *item in components.queryItems) {
            if (![item.name isEqualToString:@"path"] || !item.value.isAbsolutePath) continue;
            NSString *source = [NSString stringWithFormat:
                @"tell application id \"com.googlecode.iterm2\"\n"
                 "set newWindow to (create window with default profile)\n"
                 "tell current session of newWindow to write text (\"cd -- \" & quoted form of %@)\n"
                 "activate\n"
                 "end tell", AppleScriptString(item.value)];
            NSDictionary *error = nil;
            [[[NSAppleScript alloc] initWithSource:source] executeAndReturnError:&error];
            if (error) {
                NSAlert *alert = [[NSAlert alloc] init];
                alert.messageText = @"无法使用 iTerm 打开";
                alert.informativeText = [error[NSAppleScriptErrorMessage] description] ?: @"请检查 iTerm 的自动化权限。";
                [NSApp activateIgnoringOtherApps:YES];
                [alert runModal];
            }
        }
    }
}
@end

int main(void) {
    @autoreleasepool {
        NSApplication *application = [NSApplication sharedApplication];
        // NSApplication's delegate is weak. Keep it alive for the run loop.
        static ITermMenuDelegate *delegate;
        delegate = [[ITermMenuDelegate alloc] init];
        application.delegate = delegate;
        [application run];
    }
    return 0;
}
