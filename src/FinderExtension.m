#import <Cocoa/Cocoa.h>
#import <FinderSync/FinderSync.h>

@interface ITermFinderSync : FIFinderSync
@property(nonatomic, copy) NSArray<NSString *> *pendingPaths;
@end

@implementation ITermFinderSync
- (instancetype)init {
    if ((self = [super init])) {
        [FIFinderSyncController defaultController].directoryURLs =
            [NSSet setWithObject:[NSURL fileURLWithPath:@"/" isDirectory:YES]];
    }
    return self;
}

- (NSMenu *)menuForMenuKind:(FIMenuKind)kind {
    self.pendingPaths = @[];
    if (kind == FIMenuKindToolbarItemMenu) return nil;
    FIFinderSyncController *controller = [FIFinderSyncController defaultController];
    NSArray<NSURL *> *urls;
    if (kind == FIMenuKindContextualMenuForContainer) {
        NSURL *target = controller.targetedURL;
        urls = target ? @[target] : @[];
    } else {
        urls = controller.selectedItemURLs;
        if (!urls.count && controller.targetedURL) urls = @[controller.targetedURL];
    }
    NSMutableOrderedSet<NSString *> *paths = [NSMutableOrderedSet orderedSet];
    for (NSURL *url in urls) {
        if (!url.isFileURL) continue;
        NSNumber *isDirectory = nil;
        if (![url getResourceValue:&isDirectory forKey:NSURLIsDirectoryKey error:nil]) {
            continue;
        }
        NSURL *directory = isDirectory.boolValue ? url : url.URLByDeletingLastPathComponent;
        [paths addObject:directory.path];
    }
    if (!paths.count) return nil;
    // Finder proxies the menu across processes; representedObject does not
    // reliably survive that boundary. Keep the paths in the extension itself.
    self.pendingPaths = paths.array;
    NSMenu *menu = [[NSMenu alloc] initWithTitle:@""];
    NSMenuItem *item = [[NSMenuItem alloc] initWithTitle:@"使用iTerm打开"
                                               action:@selector(openInITerm:)
                                        keyEquivalent:@""];
    item.target = self;
    NSImage *icon = [NSImage imageWithSystemSymbolName:@"terminal" accessibilityDescription:nil];
    icon.size = NSMakeSize(16, 16);
    item.image = icon;
    [menu addItem:item];
    return menu;
}

- (void)openInITerm:(NSMenuItem *)sender {
    (void)sender;
    if (!self.pendingPaths.count) return;
    NSURLComponents *components = [[NSURLComponents alloc] init];
    components.scheme = @"genghao-open-iterm";
    components.host = @"open";
    NSMutableArray<NSURLQueryItem *> *items = [NSMutableArray array];
    for (NSString *path in self.pendingPaths) {
        [items addObject:[NSURLQueryItem queryItemWithName:@"path" value:path]];
    }
    components.queryItems = items;
    [[NSWorkspace sharedWorkspace] openURL:components.URL];
}
@end

extern int NSExtensionMain(int argc, const char *argv[]);
int main(int argc, const char *argv[]) {
    return NSExtensionMain(argc, argv);
}
