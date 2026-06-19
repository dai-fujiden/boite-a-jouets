let kanjiDict = {};
let currentPopup = null;
let popupTimer = null;
fetch(chrome.runtime.getURL("kanji_data.json"))
    .then(r => r.json())
    .then(data => {
        kanjiDict = data;
        console.log("辞書ロード完了");
    });

document.addEventListener("mouseup", e => {

    if (!e.ctrlKey) return;

    processSelection();

});

document.addEventListener("selectionchange", () => {

    clearTimeout(window._kanjiTimer);

    window._kanjiTimer = setTimeout(() => {

        if (/Android|iPhone|iPad/i.test(navigator.userAgent))
            processSelection();

    }, 800);

});


function createFloatingPanel(html, rect) {

    if (currentPopup) {
        currentPopup.remove();
        currentPopup = null;
    }

    if (popupTimer) {
        clearTimeout(popupTimer);
    }

    const panel = document.createElement("div");

    panel.className = "kanji-reader-panel";

    panel.innerHTML = html;

    panel.style.position = "absolute";

    panel.style.left =
        `${window.scrollX + rect.left}px`;

    panel.style.top =
        `${window.scrollY + rect.top - 60}px`;

    document.body.appendChild(panel);

    currentPopup = panel;

    panel.addEventListener("click", () => {

        panel.remove();
        currentPopup = null;

    });

    popupTimer = setTimeout(() => {

        if (currentPopup) {
            currentPopup.remove();
            currentPopup = null;
        }

    }, 5000);
}

async function getSettings() {

    return new Promise(resolve => {

        chrome.storage.sync.get(
            [
                "showJP",
                "showCN",
                "showKR",
                "enabled"
            ],
            resolve
        );

    });
}

async function processSelection() {

    const setting = await getSettings();

    if (!setting.enabled) return;

    const selection = window.getSelection();

    const text = selection.toString().trim();

    if (!text) return;

    const range = selection.getRangeAt(0);

    const rect = range.getBoundingClientRect();

    showReading(text, setting, rect);
}

function showReading(text, setting, rect) {
    // 漢字だけを抽出して配列にする
    const targetKanji = [];
    const jpReadings = [];
    const cnReadings = [];
    const krReadings = [];

    for (const ch of text) {
        const info = kanjiDict[ch];
        if (!info) continue; // 辞書にない文字（ひらがなや記号など）はスキップ

        targetKanji.push(ch);
        if (info.jp_on) jpReadings.push(info.jp_on);
        if (info.cn) cnReadings.push(info.cn);
        if (info.kr) krReadings.push(info.kr);
    }

    // 漢字が1つも含まれていない場合はポップアップを表示しない
    if (targetKanji.length === 0) return;

    // 表形式のHTMLを構築
    let html = `
        <table class="kr-table">
            <tr class="kr-header-row">
                <th class="kr-label">選択漢字</th>
                <td class="kr-value kr-kanji-list">${targetKanji.join(" ")}</td>
            </tr>
    `;

    // 各言語の設定が有効かつ読み方が存在する場合のみ行を追加
    if (setting.showJP && jpReadings.length > 0) {
        html += `
            <tr>
                <th class="kr-label">日本語</th>
                <td class="kr-value">${jpReadings.join(", ")}</td>
            </tr>
        `;
    }
    if (setting.showCN && cnReadings.length > 0) {
        html += `
            <tr>
                <th class="kr-label">中国語</th>
                <td class="kr-value">${cnReadings.join(", ")}</td>
            </tr>
        `;
    }
    if (setting.showKR && krReadings.length > 0) {
        html += `
            <tr>
                <th class="kr-label">韓国語</th>
                <td class="kr-value">${krReadings.join(", ")}</td>
            </tr>
        `;
    }

    html += `</table>`;

    createFloatingPanel(html, rect);
}