"""
This program fetches the last 7 days of telelog data and plots it to see if all is well.
It will also automatically send email to notify datalake administrators. 
"""
import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from matplotlib.ticker import FuncFormatter
from spillway import Spill
from model import TSModel
from sendemail import EmailHandler
from utils import load_config, save_config, get_logger

# Defaults
app_dir = 'C:/Data/telelog_monitoring'
time_zone = 'Asia/Shanghai'
plt.rcParams['figure.figsize'] = (20, 8)
plt.style.use('ggplot')

#For temporary testing in IDE, will be removed soon
#print(os.getcwd())
#os.chdir("{}/src".format(app_dir))
#print(os.getcwd())

# Get the logger and config
logger = get_logger(path=app_dir, level='INFO')
cfg = load_config(file_path='{}/conf/config.json'.format(app_dir))
logger.info('Running with config: \n{}'.format(json.dumps(cfg, indent=4)))


# An ODBC data source needs to be created beforehand to connect to the data lake PRD system.
spw = Spill(dsn='mbc_datalake_prod')

# Fetch 30 days data to train our model
dt = datetime.today() - timedelta(days=int(cfg['model']['period'])) 

query = """
SELECT dd, hour(ts) as day_hour, 
count(*) as num_records, 
count(distinct uuid) as num_sessions, 
count(distinct vin) as num_vins
FROM datalake_telelog.dw_telelog
WHERE dd >= '{}'
GROUP BY dd, hour(ts)
ORDER BY dd, day_hour ASC
""".format(dt.strftime('%Y-%m-%d'))

df = spw.execute(query)
df.to_csv('{}/data/telelog_{}.csv'.format(app_dir, datetime.today().strftime('%Y-%m-%d')))

#df = pd.read_csv('../data/telelog_2018-08-27.csv')

# Convert to type datetime and local timezone
df['dt'] = df.apply(lambda r: pd.to_datetime('{} {}:00:00'.format(r['dd'], r['day_hour'])).
                    tz_localize('UTC').tz_convert(time_zone), axis=1)

# The data in most recent hours in incompleted, therefore shuold be removed 
max_dt = pd.to_datetime('{} 00:00:00'.format(df['dt'].max().date())).tz_localize(time_zone)
df = df[df['dt'] < max_dt]

# Last 1 day for prediction
dt_pred = max_dt - timedelta(days=1) 
# Last 7 days for plot
dt_plot = max_dt - timedelta(days=7) 
logger.info('The datetime for Prediction starts from {} and the datetime for Plot starts from {}'.format(dt_pred, dt_plot))


### Handling Time Series
df = df.set_index('dt')
# Convert TS frequency to Hour 
ts_r = df['num_records'].asfreq('H', method='pad')
ts_s = df['num_sessions'].asfreq('H', method='pad')
ts_v = df['num_vins'].asfreq('H', method='pad')


### Train the model and predict the three numbers
model = TSModel(logger)
pred_r, pred_ci_r, mse_r, mse_m_r = model.predict(ts_r, dt_pred, name='Number of records')
pred_s, pred_ci_s, mse_s, mse_m_s = model.predict(ts_s, dt_pred, name='Number of sessions')
pred_v, pred_ci_v, mse_v, mse_m_v = model.predict(ts_v, dt_pred, name='Number of vins')
logger.info('Prediction done!')


### Plot and save images
ts_r_plot = ts_r[ts_r.index >= dt_plot]
ts_s_plot = ts_s[ts_s.index >= dt_plot]
ts_v_plot = ts_v[ts_v.index >= dt_plot]
      
fig = plt.figure(figsize=(20,8))
ax1 = fig.add_subplot(311)
ax1.get_yaxis().set_major_formatter(FuncFormatter(lambda x, p: format(int(x), ',')))
ax1.set_title('Number of records', fontsize=16)
ax1.xaxis.set_label_coords(1.01, -0.045)
plt.xlabel('UTC Date')
plt.plot(ts_r_plot, 'r-', label='Observed')
plt.plot(pred_r, 'orange', label='1 day ahead Forecast')
plt.legend(loc=2)
ax1.fill_between(pred_ci_r.index,
                pred_ci_r.iloc[:, 0],
                pred_ci_r.iloc[:, 1], color='k', alpha=.1)
ax2 = fig.add_subplot(312)
ax2.get_yaxis().set_major_formatter(FuncFormatter(lambda x, p: format(int(x), ',')))
ax2.set_title('Number of sessions', fontsize=16)
ax2.xaxis.set_label_coords(1.01, -0.045)
plt.xlabel('UTC Date')
plt.plot(ts_s_plot, 'b-', label='Observed')
plt.plot(pred_s, 'orange', label='1 day ahead Forecast')
plt.legend(loc=2)
ax2.fill_between(pred_ci_s.index,
                pred_ci_s.iloc[:, 0],
                pred_ci_s.iloc[:, 1], color='k', alpha=.1)                
ax3 = fig.add_subplot(313)
ax3.get_yaxis().set_major_formatter(FuncFormatter(lambda x, p: format(int(x), ',')))
ax3.set_title('Number of vins', fontsize=16)
ax3.xaxis.set_label_coords(1.01, -0.045)
plt.xlabel('UTC Date')
plt.plot(ts_v_plot, 'g-', label='Observed')
plt.plot(pred_v, 'orange', label='1 day ahead Forecast')
plt.legend(loc=2)
ax3.fill_between(pred_ci_v.index,
                pred_ci_v.iloc[:, 0],
                pred_ci_v.iloc[:, 1], color='k', alpha=.1)                 
plt.tight_layout()
img = '{}/image/{}.png'.format(app_dir, datetime.today().strftime('%Y-%m-%d'))
fig.savefig(img)


def get_inform_level():
    level = ''
    msgText = cfg['email']['strMsgText']
    thr_w_r = float(cfg['model']['threshold']['warning']['records'])
    thr_w_s = float(cfg['model']['threshold']['warning']['sessions'])
    thr_w_v = float(cfg['model']['threshold']['warning']['vins'])
    thr_e_r = float(cfg['model']['threshold']['error']['records'])
    thr_e_s = float(cfg['model']['threshold']['error']['sessions'])
    thr_e_v = float(cfg['model']['threshold']['error']['vins'])   
    
    if mse_r<thr_w_r*mse_m_r and mse_s<thr_w_s*mse_m_s and mse_v<thr_w_v*mse_m_v:
        level = 'DATA NORMAL'
        msgText = msgText.format(cfg['email']['strStatNormal'])
    elif mse_r>=thr_e_r*mse_m_r or mse_s>=thr_e_s*mse_m_s or mse_v>=thr_e_v*mse_m_v:
        level = 'DATA ERROR'
        msgText = msgText.format(cfg['email']['strStatError'])
    else:
        level = 'DATA WARNING'
        msgText = msgText.format(cfg['email']['strStatWarning'])
    return level, msgText


### Send email to notify datalake administrators
strLevel, strMsgText = get_inform_level()
logger.info('Inform level in e-mail subject is: {}'.format(strLevel))
strSubject = '[{}]{}'.format(cfg['email']['strSubJect'], strLevel)      
try: 
    emailHandler = EmailHandler()
    emailHandler.sendemail(cfg['email']['strTo'], strSubject, strMsgText, strImagePath=img, strCc=cfg['email']['strCc'])
    logger.info('Sent email succesfully at: {} UTC'.format(datetime.utcnow()))
except Exception as e:
    logger.error('ERROR: Sent email failed with {} at: {} UTC'.format(str(e), datetime.utcnow()))