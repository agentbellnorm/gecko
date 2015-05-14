import numpy as np
from numpy.linalg import norm
import pprint # for printing datq
import sys
import stockretriever
from scipy import stats
from numpy import asarray
from datetime import date
from datetime import timedelta



def get_next_day(dt): #added at 7:42
  return dt + timedelta(days=1) #added at 7:42


def to_date(strng):
    dt = strng.split('-')
    return date(dt[0], dt[1], dt[2])

def two_days_later(dt):
    return dt + timedelta(days=2)

def get_price_on_date(hist_info, dt_key, price='Open'):
    for quote in hist_info:
        dt = quote['Date']
        dt = dt.split('-')
        dt = date(int(dt[0]), int(dt[1]), int(dt[2])) 
        if dt == dt_key:
            return float(quote[price])
    
    return None


# args:
# @ scores: list of article scores
# @ pub_dates : list of python dates
# @ symbol : stock symbol
def regress(scores, pub_dates, symbol): 
    pp=pprint.PrettyPrinter(indent=4)
    hist_data = stockretriever.get_historical_info(symbol)
    y = [] # prices two days after each article was published
    for i in range(len(pub_dates)):
        dt = two_days_later(pub_dates[i-1])
        p = get_price_on_date(hist_data, dt)

        if p is None:
            scores.pop(i)
            pub_dates.pop(i)
            continue

        y.append(p)

    x = scores

    x = np.array(x) / norm(np.array(x))
    y = np.array(y) / norm(np.array(y))


    slope, intercept, r_value, p_value, std_err = stats.linregress(x,y)
    print("slope:\t%f\tintercept:\t%f\nr:\t%f\tp:\t%f\tstd_err:\t%f" % (slope, intercept, r_value, p_value, std_err))
    return slope, intercept, r_value, p_value, std_err