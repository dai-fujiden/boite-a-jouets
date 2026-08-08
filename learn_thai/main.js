function doGet() {
  return HtmlService.createHtmlOutputFromFile('index')
    .setTitle('タイ語総合クイズ')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}