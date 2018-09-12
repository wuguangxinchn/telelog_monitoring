"""
The Time Series Model based on SARIMAX

"""
import math
import numpy as np
import pandas as pd
import itertools
import warnings
warnings.filterwarnings("ignore") 
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller

class TSModel(object):
    def __init__(self, logger):  
        self.logger = logger
        
    def __test_stationarity(self, timeseries):
        #Perform Dickey-Fuller test:
        dftest = adfuller(timeseries, autolag='AIC')
        dfoutput = pd.Series(dftest[0:4], index=['Test Statistic','p-value','#Lags Used','Number of Observations Used'])
        for key,value in dftest[4].items():
            dfoutput['Critical Value (%s)'%key] = value  
        return dfoutput
      
    def predict(self, timeseries, pre_datatime, name='Number of records'):       
        ### Check Stationarity of Time Series
        # Since we are using a "grid search" to iteratively explore different combinations, and programmatically 
        # select the optimal parameter, the stationarity test can be omitted here.
        #dfoutput = self.__test_stationarity(timeseries)
        #self.logger.info('[{}] Results of Dickey-Fuller Test: \n{}'.format(name, dfoutput)) 


        ### Parameter Selection for the ARIMA Time Series Model
        p = d = q = range(0, 2)
        # Generate all different combinations of p, q and q triplets
        pdq = list(itertools.product(p, d, q))
        # Generate all different combinations of seasonal p, q and q triplets
        seasonal_pdq = [(x[0], x[1], x[2], 24) for x in list(itertools.product(p, d, q))]

        AIC = []
        SARIMAX = []
        for param in pdq:
            for param_seasonal in seasonal_pdq:
                try:
                    mod = sm.tsa.statespace.SARIMAX(timeseries,
                                                    order=param,
                                                    seasonal_order=param_seasonal,
                                                    enforce_stationarity=False,
                                                    enforce_invertibility=False)
                    results = mod.fit()
                    AIC.append(results.aic)
                    SARIMAX.append([param, param_seasonal])           
                except:
                    continue                    
        self.logger.info('[{}] The lowest AIC is {} for model SARIMAX{}x{}'.format(name,
                                                                         min(AIC),  
                                                                         SARIMAX[AIC.index(min(AIC))][0],
                                                                         SARIMAX[AIC.index(min(AIC))][1]))                                                          


        ### Fitting an ARIMA Time Series Model
        mod = sm.tsa.statespace.SARIMAX(timeseries,
                                        order=SARIMAX[AIC.index(min(AIC))][0],
                                        seasonal_order=SARIMAX[AIC.index(min(AIC))][1],
                                        enforce_stationarity=False,
                                        enforce_invertibility=False)
        results = mod.fit()
        self.logger.info('[{}] Summary of fitting the ARIMA model: \n{}'.format(name, results.summary().tables[1]))


        ### Validating Forecasts
        # Obtain the values and associated confidence intervals for forecasts of the time series.
        pred = results.get_prediction(start=pre_datatime, dynamic=True) 
        # Forecast future values  
        #pred = results.get_forecast(steps=48) 
        pred_ci = pred.conf_int() # 95% Confidence Interval

        # Ensure the predicted result is in the time range we expected 
        pred_mean = pred.predicted_mean[pred.predicted_mean.index>=pre_datatime]
        pred_ci = pred_ci[pred_ci.index>=pre_datatime]

        # Quantifing the accuracy
        y_forecasted = pred_mean
        y_truth = timeseries[timeseries.index>=pre_datatime] 
        
        # Compute the mean square error
        mse = ((y_forecasted - y_truth) ** 2).mean()
        mse_max = (y_forecasted ** 2).mean()
        mse_sqrt = math.sqrt(mse) 
        mse_max_sqrt = math.sqrt(mse_max) 
        self.logger.info('[{}] The MSE of our forecasts is {}'.format(name, round(mse, 2)))
        self.logger.info('[{}] The Square root of MSE is {}'.format(name, round(mse_sqrt, 2)))
        self.logger.info('[{}] The Max value of Square root of MSE is {}'.format(name, round(mse_max_sqrt, 2)))
        
        return pred_mean, pred_ci, mse_sqrt, mse_max_sqrt
