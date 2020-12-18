from tslearn.preprocessing import TimeSeriesScalerMeanVariance,TimeSeriesResampler
from tslearn.clustering import KShape

from matplotlib.dates import DateFormatter
import matplotlib.ticker as ticker
import matplotlib.dates as mdates

import pandas as pd 
import numpy as np
import seaborn as sns 
import matplotlib.pyplot as plt

class Kshape():
    """
    Input time_span data
    data is pd.DataFrame
    data columns are [DEVICE_DATETIME, TEMPRATURE] where DEVICE_DATETIME is index.
    data is must be sorted by index, ascendings = True.
    data has taken every 10 seconds.
    time_span = 1 means 1 timeseries = 1 minutes data.
    batch is the number of elements what using 1 timeseris has. 
    """
    def __init__(self, time_span=1, batch=60, data=None , ):
        self.time_span = time_span * 6
        self.data      = data
        self.batch     = batch
        self.km        = KShape(n_clusters=2,
                           max_iter = 50,
                           verbose=True,
                           random_state=0)
        
    def Preprocess(self,x =None):
        """
        dataを(batch, len(data)//time_span)の形に整形する。
        """
        if str(type(x)) == "<class 'NoneType'>":
            self.n_data = len(self.data)//self.time_span
            self.n_use  = self.time_span*self.n_data
            ts          = self.data.loc[:self.data.index[self.n_use -1]]
            ts          = np.array(ts.TEMPERATURE).reshape(1,-1)
            ts          = TimeSeriesScalerMeanVariance().fit_transform(ts)
            ts          = np.array(ts).reshape(self.n_data, -1)
            ts          = TimeSeriesResampler(sz=self.batch).fit_transform(ts)
            self.ts     = ts
        else:
            self.x_data = len(x)//self.time_span
            self.x_use  = self.time_span * self.x_data
            ts          = x.loc[:x.index[self.x_use -1]]
            ts          = np.array(ts.TEMPERATURE).reshape(1,-1)
            ts          = TimeSeriesScalerMeanVariance().fit_transform(ts)
            ts          = np.array(ts).reshape(self.x_data, -1)
            ts          = TimeSeriesResampler(sz=self.batch).fit_transform(ts)
            return ts

    def classification(self):
        """
        KShape で分類する。
        使わなかったデータは、TimeSeriesResampler でかさ増しして使う
        分類後に、self.data にcluster 列を作る
        """
        self.Preprocess()
        self.y_pred  = self.km.fit_predict(self.ts)
        #cluster 列を作る
        self.cluster = []
        for i in range(self.n_data ):
            list_item  = [self.y_pred[i]]*self.time_span
            self.cluster.extend(list_item)
        #データが余っている時は、Resampler で時系列データを1つだけ作って予測する。
        if not self.n_use == len(self.data):
            self.ts_c     = self.data.loc[self.data.index[self.n_use ]: ]
            self.ts_c     = np.array(self.ts_c.TEMPERATURE).reshape(1,-1)
            self.ts_batch = TimeSeriesResampler(sz=self.batch).fit_transform(self.ts_c)
            self.y_pred_c = [int(self.km.predict(self.ts_batch))]*self.ts_c.shape[1]
            self.cluster.extend(self.y_pred_c)
        self.data["CLUSTER"] = self.cluster 
        
    def draw_graph(self,x=None):
        if str(type(x)) == "<class 'NoneType'>" :
            fig, ax   = plt.subplots()
            sns.scatterplot(data=self.data, x="DEVICE_DATETIME", y="TEMPERATURE", hue="CLUSTER")
            locator   = mdates.AutoDateLocator(minticks=4, maxticks=10)
            formatter = mdates.ConciseDateFormatter(locator=locator)
            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(formatter)
            plt.show()
        else:
            fig, ax   = plt.subplots()
            sns.scatterplot(data=x, x="DEVICE_DATETIME", y="TEMPERATURE", hue="CLUSTER")
            locator   = mdates.AutoDateLocator(minticks=4, maxticks=10)
            formatter = mdates.ConciseDateFormatter(locator=locator)
            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(formatter)
            plt.show()
    
    def predict(self,x ):
        ts      = self.Preprocess(x=x)
        pred    = self.km.predict(ts)
        cluster = []
        for i in range(self.x_data ):
            list_item  = [pred[i]]*self.time_span
            cluster.extend(list_item)
        #データが余っている時は、Resampler で時系列データを1つだけ作って予測する。
        if not self.x_use == len(x):
            self.x_c     = x.loc[x.index[self.x_use ]: ]
            self.x_c     = np.array(self.x_c.TEMPERATURE).reshape(1,-1)
            self.x_batch = TimeSeriesResampler(sz=self.batch).fit_transform(self.x_c)
            y_pred_c     = [int(self.km.predict(self.x_batch))]*self.x_c.shape[1]
            cluster.extend(y_pred_c)
        x["CLUSTER"] = cluster 
        self.draw_graph(x=x)