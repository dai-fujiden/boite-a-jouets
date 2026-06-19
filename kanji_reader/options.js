const ids = [
    "showJP",
    "showCN",
    "showKR",
    "enabled"
];

document.getElementById("save")
    .addEventListener("click", () => {

        const setting = {};

        ids.forEach(id => {
            setting[id] =
                document.getElementById(id).checked;
        });

        chrome.storage.sync.set(setting, () => {
            alert("保存しました");
        });

    });

chrome.storage.sync.get(ids, s => {
    // ここでデフォルト設定をtrue or false で選択
    document.getElementById("showJP").checked =
        s.showJP ?? false;

    document.getElementById("showCN").checked =
        s.showCN ?? true;

    document.getElementById("showKR").checked =
        s.showKR ?? false;

    document.getElementById("enabled").checked =
        s.enabled ?? true;
});