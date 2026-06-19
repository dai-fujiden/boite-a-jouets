chrome.runtime.onInstalled.addListener(() => {
    chrome.contextMenus.create({
        id: "readKanji",
        title: "漢字の読みを表示",
        contexts: ["selection"]
    });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {

    chrome.tabs.sendMessage(
        tab.id,
        {
            action: "lookup",
            text: info.selectionText
        }
    );
});