---
param_guid: bf5fc479-f6df-4d49-8e20-37c6853f22cb
param_category: 
param_tags: arduino, LPST-14900
param_created: 2025-07-25 21:55:59
---

# はじめに
1年ほど前、ETS2を遊びたくて、コストコで５万ぐらいするハンコンセット(T300RS)を買った。ハンコンにはシフトレバーがついていなかったが、ハンドルの左右についている羽のようなグリッパーをシフターとして割り当てて遊んでいた。

https://www.thrustmaster.com/ja-ja/products/t300rs/

https://eurotrucksimulator2.com/

マニュアル車は免許を取得してからは一度も乗ったことはなかったが、運転している感が好きで、それをゲームでも体感できればと思っていた。だが、シフトレバーが無いことにより、ほぼ飾りと化したクラッチと、実機とは大きく異なるギア操作で、自分が求めていたユーザー体験は大きく損なわれてしまった。

そこで最近、Amazonにて[Logicoolが出しているLPST-14900なるシフター](https://gaming.logicool.co.jp/ja-jp/products/driving/driving-force-shifter.html)を購入してみた。わくわくしながらいざ開封してみると、なんと接続端子がD-Sub(9P)ではないか…！ネットを見ると、D-Sub to USBのコネクタを購入することで問題を解消している方が多く見受けられたが、そのコネクタがお値段4,500円。トータル5万以上の買い物をしておいて何をいまさらと思われるかもしれないが、自分の天邪鬼精神に火をつけた。

![[assets/images/Logicool LPST-14900のD-SubをArduinoProMicroを使いUSB接続できるようにする 1-20250725.png | Amazonの商品紹介ページ<br>接続技術の欄にはUSBと書かれていたのに…。 | 600 ]]

このような由々しき事態に対応するため、本記事では[「ゲームをやればいいじゃない(steam4.com)」様の記事](https://steam4.com/post-10065/)を参考に、手元にあったArduinoProMicro(5V 16MHz)を使って、D-Sub to USBのブリッジャーを作成する方法を記述する。

# 材料

- SparkFunが出してるArduinoProMicro(5V 16MHz)
- ジャンパーワイヤー
- シフター(LPST-14900)
- (Optional) ProMicroに履かす下駄
- (Optional) Arduino接続用のUSB micro-Bケーブル
- (Optional) ブレッドボード

![[assets/images/Logicool LPST-14900のD-SubをArduinoProMicroを使いUSB接続できるようにする 1-20250725-1.png | 今回の材料<br>ProMicroを使うのは贅沢だったかも | 300]]

今回の材料は全て自作キーボードの余り物で、Δ初期費用は0円だった。

# 準備
### (Optional)ArduinoIDEのインストールとProMicroの動作確認

[Arduino公式サイト](https://www.arduino.cc/en/software/#ide)からIDEをDLし、セットアップする。IDEが起動すると、USBのドライバ関連をインストールするか問われるので、素直に入れる。

PCとArduinoを接続し、IDEの **Tools > Port** から、接続しているUSBポート番号を選択する。今回はCOM3だったのでこれを選択。

![[assets/images/Logicool LPST-14900のD-SubをArduinoProMicroを使いUSB接続できるようにする 1-20250725-2.png | 接続ポート選択画面 | 300]]

**Tools > Get Board Info** からボード情報を取得できるようなので押下してみると、ボードは認識されているが、IDEのプリセットにはProMicroが登録されていないようだ。

![[assets/images/Logicool LPST-14900のD-SubをArduinoProMicroを使いUSB接続できるようにする 1-20250725-3.png | BN(Board Name?)がUnknownとなっている | 300]]

調べてみると、Sparkfun公式からボードファイルなるものが配布されているらしい。ありがたい。

https://github.com/sparkfun/Arduino_Boards

インストール手順に従い、**File > Preferences > Settings > Additional Boards Manager URLs** へ以下のリンクを張り付け、**OK**を押下する。
`https://raw.githubusercontent.com/sparkfun/Arduino_Boards/main/IDE_Board_Manager/package_sparkfun_index.json`

**Tools > Boards > Boards Manager** でボードマネージャーが展開されるので、Boards Managerのテキストボックスへ「sparkfun」と入力し、SparkFun AVR Boards by SparkFun Electronicsを探す。特殊な状況を除き、バージョンは最新のものを選択すれば問題ないだろう。**INSTALL**を押下するとインストールが開始される。

![[assets/images/Logicool LPST-14900のD-SubをArduinoProMicroを使いUSB接続できるようにする 1-20250725-4.png | ボードの追加画面 | 500]]

正常にインストールされると、**Tools > Boards** に「SparkFun AVR Boards」が追加されているはずだ。今回接続しているボードはProMicroなので、**SparkFun AVR Boards > SparkFun Pro Micro** を選択する。

![[assets/images/Logicool LPST-14900のD-SubをArduinoProMicroを使いUSB接続できるようにする 1-20250725-5.png | ボードマネージャーから追加したSparkFunのボードらが選択可能になっている状態 | 500]]

**Tools > Processor** から、今回使用している「ATmega32U4(5V 16 MHz)」を選択し、**Reload Board Data** してから**Get Board Info** したが、Unknownのままだった。ボードデータは追加したプリセットから読んでいると思ったが、接続しているボードから呼び出しているのだろうか？きちんと接続されているか不安なので、ボードにデフォルトで配置されているLEDを点滅できるか確かめてみる。

```cpp
/*
  https://cdn.sparkfun.com/assets/f/d/8/0/d/ProMicro16MHzv2.pdf
*/

#define TX_LED 30
#define RX_LED 17

void setup() {
  pinMode(TX_LED, OUTPUT);
  pinMode(RX_LED, OUTPUT);
}

void loop() {
  digitalWrite(TX_LED, LOW);  // turn the TX LED on
  delay(1000);
  digitalWrite(TX_LED, HIGH); // turn the TX LED off
  digitalWrite(RX_LED, LOW);  // turn the RX LED on
  delay(1000);
  digitalWrite(RX_LED, HIGH); // turn the RX LED off
  delay(1000);
}
```

上記のコードを張り付け、Uploadでボードに書き込む。書き込み完了後、ボードを見ると、図のRX LEDとTX LEDが交互に点滅していることが確認できた。接続に問題は無いようだ。

![[assets/images/Logicool LPST-14900のD-SubをArduinoProMicroを使いUSB接続できるようにする 1-20250725-6.png | 参考：https://cdn.sparkfun.com/assets/f/d/8/0/d/ProMicro16MHzv2.pdf | 600]]

スケッチを書き込んだ際に出力される文字列が赤文字なため、一瞬エラーが出てしまったと思った。なんと紛らわしい…。せめて緑色とかにしてくれ。

### シフコン操作用のスケッチを適用

[一次ソースのYouTube](https://www.youtube.com/watch?v=dLpWEu8kCec)動画概要欄に記述のあるGitHubへアクセスし、スケッチをデバッグしてみる。  
メインコード: [https://github.com/AM-STUDIO/LOGITECH_USB_ADAPTER](https://github.com/AM-STUDIO/LOGITECH_USB_ADAPTER)  
ライブラリ: [https://github.com/MHeironimus/ArduinoJoystickLibrary](https://github.com/MHeironimus/ArduinoJoystickLibrary)

ライブラリはzipで落とし、**Sketch > Include Library > Add .ZIP Library…** から選択、ロードを行う。

![[assets/images/Logicool LPST-14900のD-SubをArduinoProMicroを使いUSB接続できるようにする 1-20250725-7.png | zipで落としたライブラリをIDEにインクルード | 400]]

メインコードをIDEに張り付け、コンパイル(Verify)とArduinoへの書き込み(Upload)が成功した。一通り準備は整ったので、次は配線だ。

（今さらだが、今回利用するジョイスティックライブラリは、ATmega32U4ベースのサポートを行っているため、本ボードで問題なく動作する。他バージョンやナンバリングのマイコンを搭載したArduinoでは動作しない可能性があるので注意が必要だ。）

## 配線

褒められた方法ではないが、ブレッドボードに下駄を差した状態ではんだ付けをすると便利

![[assets/images/Logicool LPST-14900のD-SubをArduinoProMicroを使いUSB接続できるようにする 1-20250725-8.png | 熱でブレッドボードが変形する可能性があるが、利便性の前では無視できるのだ | 300]]

元ネタではArduino LEONARDを使ったスケッチになっているが、利用するピンが少ないこともあり、そのまま流用できる。接続は以下の通りだ。

![[assets/images/Logicool LPST-14900のD-SubをArduinoProMicroを使いUSB接続できるようにする 1-20250725-9.png | 色付きの番号が各D-Subのピンに対応している | 400]]


D-SubとArduinoの接続対応表

| D-Sub | Arduino |
| ----- | ------- |
| 1     | not use |
| 2     | D2      |
| 3     | 5V      |
| 4     | A0      |
| 5     | not use |
| 6     | GND     |
| 7     | 5V      |
| 8     | A2      |
| 9     | not use |

![[assets/images/Logicool LPST-14900のD-SubをArduinoProMicroを使いUSB接続できるようにする 1-20250725-10.png | 実機の様子<br>ジャンパがゆるゆるで、手で押さえていないと抜けてしまうズボラ仕様 | 400]]

# 動作確認

### 呪文

動作確認を行うのに「デバイスとプリンター」項目を開く必要があるそうだが、見つからない…。偉大なるネットの先人達に聞いたところ、どうやら項目を実装しているDeviceCenter.dllに割り当てられたGUIDを呼び出すことで、一発で到達できるようだ！

https://denor.jp/windows-11%E3%81%A7%E3%82%B3%E3%83%B3%E3%83%88%E3%83%AD%E3%83%BC%E3%83%AB%E3%83%91%E3%83%8D%E3%83%AB%E3%80%8C%E3%83%87%E3%83%90%E3%82%A4%E3%82%B9%E3%81%A8%E3%83%97%E3%83%AA%E3%83%B3%E3%82%BF%E3%83%BC

早速、Win+Rでコマンドパレットを開き、以下の呪文を唱える。
`shell:::{A8A91A66-3A7D-4424-8D24-04E180695C7A}`

![[assets/images/Logicool LPST-14900のD-SubをArduinoProMicroを使いUSB接続できるようにする 1-20250725-11.png | こうでもしないとたどり着けなかったのは何で…? | 300]]

おぉ、なんということだ。一発で「デバイスとプリンター」に到達してしまったではないか。今日一番の感動である。

![[assets/images/Logicool LPST-14900のD-SubをArduinoProMicroを使いUSB接続できるようにする 1-20250725-12.png | 呪文により突如出現した「デバイスとプリンター」<br>（使用中の周辺デバイス名を晒すのはセキュリティ上よろしくないぞ！） | 500]]

### コントローラテスターでの確認

デバイス一覧に「SparkFun Pro Micro」が存在していれば、これを右クリックし、**ゲームコントローラーの設定 > プロパティ** にて、テスターが出現するはずだ。

![[assets/images/Logicool LPST-14900のD-SubをArduinoProMicroを使いUSB接続できるようにする 1-20250725-13.png | こんな機能初めて見た | 500]]

接続を確認し、シフターをぐりぐり動かしてみる。

![[assets/images/logi_shifter_test.gif | 挙動が変だが動いた！ | 500]]

挙動が若干怪しいが、問題なく動作することが確認できた。  
本記事が、少しでも参考になれば幸いである。

# 課題点

実際に動作確認をしてみて、いくつかの改善点があった。

1. ジャンパワイヤーがスカスカですぐ抜けるし、配線がむき出しで格好悪い
    
2. メインコードの閾値が微妙で、特にギアを3, 4に入れたときおかしくなる
    
3. ギアをRに入れる場合、スティックを押し込んでからRに入力する必要があるのだが、押し込んだ瞬間にR判定となってしまう
    

これらの改善点は次回の投稿に持ち越そうと思う。

# 備考

今回SparkFunProMaxの配線を描画するのに、Wokwi.comというサービスを利用した。初期プリセットでは該当するモデルが無かったため自作してみた。参考程度にフォークしたブランチを置いておく

https://github.com/TANUKIpro/wokwi-boards/pull/1
