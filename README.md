# raz-pai-dht11-gcp
ラズベリーパイ+dht11 が測定した温湿度データをBigQueryに保存している。  
そのデータと機械学習を使って遊んでみる 
# コンテンツ
1. [前置き](#1-前置き)
2. [構造](#2-構造)
3. [やったこと](#3-やったこと)

## 1. 前置き
ビッグデータに触ってみたい、自分で用意するのに楽な方法はないかな？と思った時、ラズベリーパイにデータを取得させよう!と思いついた。ラズベリーパイ+dht11で室温を計測し、BigQueryにデータを保存している。それをgoogle datastudio で監視しながら、データが集まったら、エアコンの稼働時間を推定する、という問題を解いてみる。  
[google datastudioのリンク](https://datastudio.google.com/reporting/cef87383-cb89-43fc-81f6-eb103631d43d)  
GCPの使い方については[この本](https://misoton.booth.pm/items/1850809)を参考にしています。  

## 2. 構造
ラズベリーパイとdht11 を接続して、温度データを取得する。  
GCPの機能を利用して、BigQuery にデータを保存する。  
google の提供するdatastudioでデータを監視する。  
データをダウンロードして解析する。  
![構成](/img/architecture.png)
## 3 やったこと
### 3.1 BigQueryの準備
projectを立ち上げ、APIを有効化する。BigQueryの画面で  
データセットを作成→テーブルを作成  
ラズベリーパイから温度と湿度を受け取るので、スキーマは以下のように設定する.
![スキーマの設定](/img/スキーマ_txt.jpg)![スキーマの設定](/img/スキーマ.jpg) 
### 3.2 Pub/Subの設定とCloudFunctions の作成
Pub/Sub で、トピックを作成したらcloudshell を立ち上げ、Pub/sub とBigQueryを繋ぐ関数をデプロイする。作成した関数は、[iotcollector.go](iotcollector.go)。  
cloudshell 上で、
~~~
go mod init modules
~~~
iotcollector.goを配置して、
~~~
go build
gcloud functions deploy CollectDeviceData\
 --runtime go111\
  --trigger-topic topic-name 
  ~~~
でデプロイする。topic-name には、Pub/Subで指定したトピック名を入れる。  
cloudshell 上で
~~~
gcloud pubsub topics publish topic-name \
--message \
'{"ID": 111 ,
"DEVICE_DATETIME": "2020-12-31T14:11:03",
"TEMPERATURE": 11.11,
"HUMIDITY": 30.00
}'
~~~
~~~
bq query \
'SELECT * FROM dataset-name.table-name '
~~~
として、関数が上手く動いているか確かめる事が出来る。  
ただし、dataset-name は、[3.1](###31-BigQueryの準備)で作ったデータセットや、テーブルの名前。
### 3.3 IoTCoreの設定
IoTCore でラズベリーパイとPub/Subが暗号化した通信が出来るように設定する。  
初めにラズベリーパイ側で公開鍵と暗号鍵を作成する。
~~~
openssl req -x509 -newkey rsa:2048 -keyout rsa_private.pem -nodes \
-out rsa_cert.pem -subj "/CN=unused"
~~~
IoTCore にレジストリを作成し、デバイスを登録する。  
この時、ラズベリーパイ側で作成された鍵を張り付ける。
![公開鍵の設定](/img/key.jpg) 
### 3.4. ラズベリーパイからデータの送信
ラズベリーパイ側で、プログラムを走らせてデータを送信する。  
pythonで[プログラム](/razpai/data_sender.py)を書いた。  
dht11 からデータを取得する所以外は、cloudshell 上にある  
python-docs-samples/iot/api-client/http_example/cloudiot_http_example.py  
による。このサンプルは[github](https://github.com/GoogleCloudPlatform/python-docs-samples)でも公開されている。
プログラムを走らせるため、以下のようなディレクトリを作る。  
~~~
.
├── data_sender.py
├── data_sender.sh
├── dht11
├── requirements.txt
├── rsa_cert.pem
├── rsa_private.pem
~~~
data_sender.sh にプロジェクトidなどを入力して、以下を実行する。
~~~
pip install requirements.txt
chmod +x data_sender.sh
bash data_sender.sh
~~~
これで、10秒毎にデータがBigQueryに登録される。  
データの蓄積を可視化するのに、googleのサービス、datastudioを使う。

### 3.5. BigQuery とdatastudio の連携
初めに、[datastudio](https://datastudio.google.com/)にログインする。(今はData Portal と呼ぶみたいです。)  
ログインしたらデータソース→BigQuery→作ったデータセット→作ったテーブル  
と選択して、接続を選ぶ。  接続したら、ディメンションを設定する。  
![ディメンションの設定](/img/dimension.jpg) 
レポートを作成、をクリックして良い感じのレポートを作る。  
今回作ったレポートは[ここ](https://datastudio.google.com/reporting/cef87383-cb89-43fc-81f6-eb103631d43d)から見れる。
### 3.6. データ解析の為のモデル作成
12/16時点のレポートのグラフ。  
![レポート](/img/report.jpg) 
冬なので、エアコン(暖房)を付けていない時は温度が下がり、付けている時は上がっている事が分かる。  
これを見るだけで、エアコンが付いているかどうかは一目瞭然だが、機械学習で見分けるという話だったので、モデルを作成する。  
今回は温度が下がり続ける時系列データと、温度が上がり続ける時系列データで分類できれば良いので、[tslearn](https://tslearn.readthedocs.io/en/stable/) の[KShape](https://tslearn.readthedocs.io/en/stable/auto_examples/clustering/plot_kshape.html?highlight=kshape) というモデルを使った。  
時系列データの前処理としては、1分を一区切り、時系列データの要素数は60個として、データを分割した。詳しい実装は、[src/train_model.py](/src/train_model.py) に書いてある。  
トレーニングしたモデルは、`src/trained_model.hdf5`に保存してある。  
遊んでみたい時は、srcフォルダ内で
~~~
pip install requirements
~~~
して、src内の[Jupyter Notebook](/src/draw_graph.ipynb)のセルを全て実行すると良い。  
### 実行結果  
![グラフ](/img/graph.jpg)   
やったね！




