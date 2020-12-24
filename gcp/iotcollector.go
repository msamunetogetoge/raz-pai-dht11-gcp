package iotcollector

import (
	"context"
	"encoding/json"
	"log"
	"os"
	"time"

	//BiqQuery を操作するのに必要なライブラリ
	"cloud.google.com/go/bigquery"
	"cloud.google.com/go/civil"
)

type PubSubMessage struct {
	Data []byte `json:"data"`
}

type Info struct {
	ID             int            `json:"ID" bigquery:"ID"`
	DeviceDatetime civil.DateTime `json:"DEVICE_DATETIME" bigquery:"DEVICE_DATETIME"`
	Temperature    float64        `json:"TEMPERATURE" bigquery:"TEMPERATURE"`
	Humidity       float64        `json:"HUMIDITY" bigquery:"HUMIDITY"`
	Timestamp      time.Time      `bigquery:"TIMESTAMP"`
}

func CollectDeviceData(ctx context.Context, m PubSubMessage) error {
	var i Info
	//json 形式のメッセージを構造体へ格納する
	err := json.Unmarshal(m.Data, &i)
	//エラー時はエラーの型とエラー内容をLogging へ出⼒する
	if err != nil {
		log.Printf("メッセージ変換エラー Error:%T message: %v", err, err)
		return nil
	}
	//BigQuery にデータを追加する関数を呼び出す
	InsertBigQuery(&ctx, &i)
	return nil
}

func InsertBigQuery(ctx *context.Context, i *Info) {
	//プロジェクトID を取得する
	projectID := os.Getenv("GCP_PROJECT")
	//BigQuery を操作するクライアントを作成する、エラーの場合はLogging へ出⼒する
	client, err := bigquery.NewClient(*ctx, projectID)
	if err != nil {
		log.Printf("BigQuery 接続エラー Error:%T message: %v", err, err)
		return
	}
	//確実にクライアントを閉じるようにする
	defer client.Close()
	//クライアントからテーブルを操作するためのアップローダーを取得する
	u := client.Dataset("temp_hmdt").Table("ENV_DATA").Uploader()

	//現在時刻を構造体へ格納する
	i.Timestamp = time.Now()
	items := []Info{*i}
	//テーブルへデータの追加を⾏う、エラーの場合はLogging へ出⼒する
	err = u.Put(*ctx, items)
	if err != nil {
		log.Printf("データ書き込みエラー Error:%T message: %v", err, err)
	}
}
