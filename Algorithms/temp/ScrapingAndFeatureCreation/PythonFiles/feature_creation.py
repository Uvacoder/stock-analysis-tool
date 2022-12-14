import numpy as np
import pandas as pd
import os
import re
import math
import traceback
import datetime
import multiprocessing
from multiprocessing.pool import ThreadPool

path = os.path.join(os.getcwd(), os.path.join("Data", "GRStock"))

if not os.path.exists(path):
    os.makedirs("Data/GRStock")

path = os.path.join(os.getcwd(), os.path.join("Data"))

def drop_duplicate_rows(df):
    """
    Drops the duplicate rows in the dataframe based on Date column.
    Parameters
    ----------
    df : dataframe
    Returns
    -------
    df: dataframe
        updated dataframe after droping duplicates.
    """
    df = df.drop_duplicates(subset=["Date"], keep="first")
    return df


def fill_with_previous_values(df):
    """
    Fills the null values in the dataframe with the values from the previous row.
    Parameters
    ----------
    df : dataframe
    Returns
    -------
    df : dataframe
        updated dataframe after filling with previous values.
    """
    df.fillna(method="ffill", inplace=True)
    return df


def add_missing_rows(df, ind):
    """
    Adds rows to the stock dataframe.
    If the date is present in index dataframe an not present in stock dataframe,
    then a new row (as date and NAN values) is added to stock dataframe.
    Parameters
    ----------
    df : dataframe
        stock dataframe
    ind : dataframe
        index dataframe
    Returns
    -------
    df : dataframe
        updated dataframe after adding new rows.
    """

    df.Date = pd.to_datetime(df.Date)
    ind.Date = pd.to_datetime(ind.Date)
    s = df.Date.head(1).values[0]
    e = df.Date.tail(1).values[0]
    ind = ind[ind.Date.between(e, s)]
    missing_df = pd.DataFrame(columns=df.columns)
    indexes_dates = ind.Date.values
    df.Date = pd.to_datetime(df.Date)
    df_dates = df.Date.values
    start = 0
    for i, v in enumerate(indexes_dates):
        if v not in df.Date.values:
            m = abs(ind.shape[1]-missing_df.shape[1])
            res = list(np.append(ind.iloc[i].values, [np.nan]*m))
            missing_df.loc[start] = res
            start += 1
    df = pd.concat([df, missing_df])
    return df


def cleaning(df, ind):
    """
    Removes duplicate rows, Adds missing rows, fills null values from pervious row to the stock dataframe.
    Parameters
    ----------
    df : dataframe
        stock dataframe
    ind : dataframe
        index dataframe
    Returns
    -------
    df : dataframe
        updated dataframe after performing all the operations.
    """

    df = drop_duplicate_rows(df)
    ind = drop_duplicate_rows(ind)
    df = add_missing_rows(df, ind)
    df = fill_with_previous_values(df)
    df.reset_index(drop=True, inplace=True)
    df = drop_duplicate_rows(df)
    df = df.sort_values(by=["Date"], ascending=[False])
    return df, ind

def bonus_issue(stock, start_date, end_date, r1, r2):
    """
    For an r1:r2 bonus shares,
    if y is the stock value before the bonus share issue,
    then the value of the stock will be y*(r2/(r1+r2)),
    for the data between the given dates.
    Parameters
    ----------
    stock : dataframe
    start_date : datetime
    end_date : datetime
    r1 : integer
    r2 : integer
    Returns
    -------
    stock : dataframe
        updated dataframe after bonus
    """
    specific_dates = stock[stock.Date.between(end_date, start_date)]
    for index, row in specific_dates.iterrows():
        specific_dates.loc[index, "Open Price"] = specific_dates.loc[index,
                                                                     "Open Price"] * (r2/(r1+r2))
        specific_dates.loc[index, "Low Price"] = specific_dates.loc[index,
                                                                    "Low Price"] * (r2/(r1+r2))
        specific_dates.loc[index, "High Price"] = specific_dates.loc[index,
                                                                     "High Price"] * (r2/(r1+r2))
        specific_dates.loc[index, "Close Price"] = specific_dates.loc[index,
                                                                      "Close Price"] * (r2/(r1+r2))
        specific_dates.loc[index,
                           "WAP"] = specific_dates.loc[index, "WAP"] * (r2/(r1+r2))
        stock.loc[index] = specific_dates.loc[index]
    return stock


def stock_split(stock, start_date, end_date, r1, r2):
    """
    For an r1:r2 stock split, if y is the stock value before the split,
    then the value of the stock will be y*(r1/r2),
    for the data between the given dates.
    Parameters
    ----------
    stock : dataframe
    start_date : datetime
    end_date : datetime
    r1 : integer
    r2 : integer
    Returns
    -------
    stock : dataframe
        updated dataframe after splitting
    """
    specific_dates = stock[stock.Date.between(end_date, start_date)]
    for index, row in specific_dates.iterrows():
        specific_dates.loc[index,
                           "Open Price"] = specific_dates.loc[index, "Open Price"] * (r1/r2)
        specific_dates.loc[index,
                           "Low Price"] = specific_dates.loc[index, "Low Price"] * (r1/r2)
        specific_dates.loc[index,
                           "High Price"] = specific_dates.loc[index, "High Price"] * (r1/r2)
        specific_dates.loc[index, "Close Price"] = specific_dates.loc[index,
                                                                      "Close Price"] * (r1/r2)
        specific_dates.loc[index,
                           "WAP"] = specific_dates.loc[index, "WAP"] * (r1/r2)
        try:
            stock.loc[index] = specific_dates.loc[index]
        except:
            traceback.print_exc()

    return stock


def create_dividend(stock, corporate):
    """
    Creates new Dividend Value column in the stock dataframe.
    Parameters
    ----------
    corporate : dataframe
    stock : dataframe
    Returns
    -------
    stock : dataframe
        updated dataframe with dividend column
    """
    corporate['Ex Date'] = pd.to_datetime(
        corporate['Ex Date'], errors='coerce')
    stock['Date'] = pd.to_datetime(stock['Date'], errors='coerce')

    dividend = corporate[corporate['Purpose'].str.contains("Dividend")]
    result = {}
    for index, row in dividend.iterrows():
        try:
            year = row["Ex Date"].year
            month = row["Ex Date"].month
            amount = re.findall(r"\d+.?\d*", row["Purpose"])[0]
            res = result.get(year, {})
            q = "1q" if 1 <= month <= 3 else "2q" if 4 <= month <= 6 else "3q" if 6 <= month <= 9 else "4q"
            val = res.get(q, [])
            val.append(float(amount))
            res[q] = val
            result[year] = res
        except:
            pass

    for year, quaters in result.items():
        for q, a in quaters.items():
            quaters[q] = sum(a)/len(a)
        result[year] = quaters
    divList = list()
    for index, row in stock.iterrows():
        year = row["Date"].year
        month = row["Date"].month
        q = "1q" if 1 <= month <= 3 else "2q" if 4 <= month <= 6 else "3q" if 6 <= month <= 9 else "4q"
        if result.get(year) != None:
            if result.get(year).get(q) != None:
                divList.append(result.get(year).get(q))
            else:
                divList.append(0)
        else:
            divList.append(0)
    stock["Dividend Value"] = divList
    return stock


def apply_corporate_actions(stock, corporate):
    """
    Applies stock split and bonus on the given stock dataset.
    creates bonus dataframe and invoke bonus_issue method.
    creates split dataframe and invoke stock_split method.
    creates dividend value Column in Stock dataframe by invoking create_dividend method.
    Parameters
    ----------
    stock : dataframe
    corporate : dataframe
    Returns
    -------
    stock : dataframe
        updated dataframe after stock split and bonus and dividend.
    Methods
    -------
    stock_split : 
    bonus_issue :
    """
    stock["Date"] = pd.to_datetime(stock["Date"])
    corporate["Ex Date"] = pd.to_datetime(
        corporate["Ex Date"], errors='coerce')
    # corporate["BC Start Date"] = pd.to_datetime(corporate["BC Start Date"],errors='coerce')
    # corporate[" BC End Date\t"] = pd.to_datetime(corporate[" BC End Date\t"],errors='coerce')
    # corporate["ND Start Date"] = pd.to_datetime(corporate["ND Start Date"],errors='coerce')
    # corporate["ND End Date"] = pd.to_datetime(corporate["ND End Date"],errors='coerce')

    bonus_df = corporate[corporate['Purpose'].str.contains("Bonus")]
    for index, row in bonus_df.iterrows():
        start_date = bonus_df.loc[index, "Ex Date"]
        ratio = bonus_df.loc[index, "Purpose"]
        r1, r2 = re.findall(r"\d+", ratio)
        r1, r2 = int(r1), int(r2)
        end_date = stock.tail(1)["Date"].values[0]
        stock = bonus_issue(stock, start_date, end_date, r1, r2)

    stock_split_df = corporate[corporate['Purpose'].str.contains("Stock")]
    for index, row in stock_split_df.iterrows():
        start_date = stock_split_df.loc[index, "Ex Date"]
        ratio = stock_split_df.loc[index, "Purpose"]
        r1, r2 = re.findall(r"\d+", ratio)
        r1, r2 = int(r1), int(r2)
        end_date = stock.tail(1)["Date"].values[0]
        stock = stock_split(stock, start_date, end_date, r1, r2)

    stock = create_dividend(stock, corporate)

    return stock


def calculate_beta(stock, ind):
    """
    Creates a new Beta column in the stock dataframe
    beta = covariance(X, Y)/var(Y)
    X = %returns of company
    Y = %returns of sp500
    %returns of company = ((Close Price of today / Close Price of previous trading day) - 1) * 100
    %returns of sp500 = from new Index dataframe. (% Return)
    Parameters
    ----------
    stock : dataframe
    Returns
    -------
    stock : dataframe
        updated dataframe with new Beta column
    """
    # path = os.path.join(os.getcwd(), "Data")

    stock["% Return of Company"] = (
        (stock["Close Price"] / stock['Close Price'].shift(1))-1)*100
    # ind = pd.read_csv(os.path.join(path, "Index.csv"))
    ind["Date"] = pd.to_datetime(ind["Date"])
    s = stock.Date.head(1).values[0]
    e = stock.Date.tail(1).values[0]
    ind = ind[ind.Date.between(e, s)]
    ind.rename(columns={'Close': 'Close Price of SP500',
               '% Return': '% Return of SP500'}, inplace=True)
    ind.drop(['Open', 'High', 'Low', '% YTD'], axis=1, inplace=True)
    ind["Date"] = pd.to_datetime(ind["Date"])
    stock["Date"] = pd.to_datetime(stock["Date"])
    stock = pd.merge(stock, ind, on="Date", how="left")

    sp500 = stock["% Return of SP500"]
    company = stock["% Return of Company"]
    results = list()
    for i in range(stock.shape[0]):
        # cov = np.cov(company[i:],sp500[i:])[0][1]
        cov = np.ma.cov(np.ma.masked_invalid(
            np.array(company[i:], sp500[i:])), rowvar=False)
        var = np.nanvar(sp500[i:])
        res = var/cov
        results.append(res)
    stock["Beta"] = results
    return stock


def add_risk_free_column(stock, riskrates):
    """
    Creates a new Rate column in the stock dataframe using riskfreerate file.
    Parameters
    ----------
    stock : dataframe
    Returns
    -------
    res : dataframe
        updated dataframe with Rate column
    """
    # path = os.path.join(os.getcwd(), "Data")

    # riskrates = pd.read_csv(os.path.join(path, "RiskFreeRate.csv"))
    riskrates["Date"] = pd.to_datetime(riskrates["Date"])
    stock["Date"] = pd.to_datetime(stock["Date"])
    # riskrates["Rate"] = pd.to_numeric(riskrates["Rate"])
    riskrates["Rate"] = (riskrates["Rate"].astype(
        str)).apply(pd.to_numeric, errors='coerce')
    # stock[direct_columns] = (stock[direct_columns].astype(
    #     str)).apply(pd.to_numeric, errors='coerce')
    res = pd.merge(stock, riskrates, on="Date", how="left")
    return res


def calculate_alpha(stock, ind):
    """
    Creates a new Alpha column in the stock dataframe
    alpha = %YTDCompany - (riskfreerate + (Beta * (%YTDSP500 - riskfreerate)))
    %YTDCompany = percentage of year to date of the company
    %YTDSP500 = percentage of year to date of the index file.(%YTD)
    Beta = beta value from calculate_beta method.
    %YTDCompany = ((Close Price of last available day / Close Price of today) - 1) * 100
    riskfreerate : 
    Parameters
    ----------
    stock : dataframe
    Returns
    -------
    stock : dataframe
        updated dataframe with new Alpha column
    """
    # path = os.path.join(os.getcwd(), "Data")

    stock["% YTD of Company"] = (
        (stock.tail(1)['Close Price'].values[0]/stock["Close Price"])-1)*100
    # ind = pd.read_csv(os.path.join(path, "Index.csv"))
    ind["Date"] = pd.to_datetime(ind["Date"])
    s = stock.Date.head(1).values[0]
    e = stock.Date.tail(1).values[0]
    ind = ind[ind.Date.between(e, s)]
    ind.drop(['Open', 'High', 'Low', "Close",
             "% Return"], axis=1, inplace=True)
    ind.rename(columns={'% YTD': '% YTD of SP500'}, inplace=True)
    ind["Date"] = pd.to_datetime(ind["Date"])
    stock["Date"] = pd.to_datetime(stock["Date"])
    stock = pd.merge(stock, ind, on="Date", how="left")
    # stock["Beta"] = pd.to_numeric(stock["Beta"], errors='coerce')
    stock["Beta"] = (stock["Beta"].astype(
        str)).apply(pd.to_numeric, errors='coerce')
    stock["Alpha"] = stock["% YTD of Company"] - \
        (stock["Rate"]+(stock["Beta"]*(stock["% YTD of SP500"] - stock["Rate"])))
    return stock


def create_lower_band(stock):
    """
    Creates new lower band column in the stock dataframe.
    Parameters
    ----------
    stock : dataframe
    Returns
    -------
    stock : dataframe
        updated dataframe with lower band column
    """

    # sorted_data = pd.DataFrame()
    # sorted_data["Date"] = stock["Date"]
    # sorted_data["Close Price"] = stock["Close Price"]
    # sorted_data["Date"] = pd.to_datetime(sorted_data["Date"])
    # stock["Date"] = pd.to_datetime(stock["Date"])
    # sorted_data = sorted_data.sort_values(['Close Price', 'Date'], ascending=[True, False])
    # start_date = stock.tail(1)["Date"].values[0]

    stock["Lower Band"] = ""
    for i, row in stock.iterrows():
        # end_date = row["Date"]
        # close_price = row["Close Price"]
        stock.loc[i, "Lower Band"] = min(stock.loc[i:]["Close Price"])
        # specific_dates = stock[stock.Date.between(start_date,end_date)]
        # for index,j in specific_dates.iterrows():
        #     stock.iloc[index,"Lower Band"] = close_price
    return stock


def create_upper_band(stock):
    """
    Creates new upper band column in the stock dataframe.
    Parameters
    ----------
    stock : dataframe
    Returns
    -------
    stock : dataframe
        updated dataframe with upper band column
    """
    # sorted_data = pd.DataFrame()
    # sorted_data["Date"] = stock["Date"]
    # sorted_data["Close Price"] = stock["Close Price"]
    # sorted_data["Date"] = pd.to_datetime(sorted_data["Date"])
    # stock["Date"] = pd.to_datetime(stock["Date"])
    # sorted_data = sorted_data.sort_values(['Close Price', 'Date'], ascending=[False, True])
    # end_date = stock.tail(1)["Date"].values[0]
    stock["Upper Band"] = ""
    for i, row in stock.iterrows():
        # start_date = row["Date"]
        # close_price = row["Close Price"]
        stock.loc[i, "Upper Band"] = max(stock.loc[i:]["Close Price"])
        # specific_dates = stock[stock.Date.between(start_date,end_date)]
        # for index,j in specific_dates.iterrows():
        # stock.loc[index,"Upper Band"] = close_price
    return stock


def calculate_band_area(stock):
    """
    Creates new band area column in the stock dataframe.
    Parameters
    ----------
    stock : dataframe
    Returns
    -------
    stock : dataframe
        updated dataframe with band area column
    """
    # stock["Upper Band"] = pd.to_numeric(stock["Upper Band"])
    # stock["Lower Band"] = pd.to_numeric(stock["Lower Band"])
    stock[["Upper Band", "Lower Band"]] = (stock[["Upper Band", "Lower Band"]].astype(
        str)).apply(pd.to_numeric, errors='coerce')
    stock["Band Area"] = stock["Upper Band"]-stock["Lower Band"]
    return stock


def create_lower_upper_bands(stock):
    """
    Creates lower band, upper band, band area columns in the stock dataframe.
    Parameters
    ----------
    stock : dataframe
    Returns
    -------
    stock : dataframe
        updated dataframe with lower, upper, band area columns
    """
    stock["Lower Band"] = ""
    stock["Upper Band"] = ""
    stock["Band Area"] = ""

    for i, row in stock.iterrows():
        maxv = max(stock.loc[i:]["Close Price"])
        minv = min(stock.loc[i:]["Close Price"])
        stock.loc[i, "Upper Band"] = maxv
        stock.loc[i, "Lower Band"] = minv
        stock.loc[i, "Band Area"] = maxv - minv
    return stock


def create_eps_pe_ratio_revenue_income_expenditure_net_profit(rev, stk):
    """
    Creates eps, pe, revenue, income, expenditure, profit columns.
    Creates 2,4,8 bands for eps, pe, revenue, income, expenditure, profit columns.
    Parameters
    ----------
    rev : dataframe
        revenue dataframe
    stk : dataframe
        stock dataframe
    Returns
    -------
    stk : dataframe
        updated dataframe after creating the columns.
    """

    stk["Date"] = pd.to_datetime(stk["Date"])
    s = min(rev.year)
    e = max(rev.year)
    cols = ['Revenue', 'Income', 'Expenditure', 'Net Profit', 'EPS']
    stk[cols] = pd.DataFrame([[0]*len(cols)], index=stk.index)

    rep = ['revenue', 'income', 'expenditure', 'profit', 'eps']

    for index, row in stk.iterrows():
        q = (row.Date.month-1)//3 + 1
        samp = rev[(rev['year'] == row.Date.year) & (rev['quartile'] == q)]
        if samp.shape[0] != 0:
            stk.loc[index, cols] = samp.iloc[0][rep].values
        else:
            stk.loc[index, cols] = [np.nan]*5

    stk['year'] = pd.DatetimeIndex(stk['Date']).year
    # stk = stk[(stk.year >= s)&(stk.year <= e) & stk["Revenue"] !=0 ]
    # stk = stk.drop(["year"],axis=1)

    bands = [2, 4, 8]

    for band in bands:
        bcols = ['Revenue last '+str(band)+' quarters', 'Income last '+str(band)+' quarters', 'Expenditure  last '+str(
            band)+' quarters', 'Net Profit  last '+str(band)+' quarters', 'EPS last '+str(band)+' quarters']
        stk[bcols] = pd.DataFrame([[0]*len(bcols)], index=stk.index)

        for index, row in stk.iterrows():
            q = (row.Date.month-1)//3 + 1
            samp = rev[(rev['year'] == row.Date.year) & (rev['quartile'] == q)]
            if samp.shape[0] == 0:
                r = 1
            else:
                r = samp.index.values[0]
            if r+band+1 < rev.shape[0]:
                v = range(r+1, r+band+1)
                stk.loc[index, bcols] = rev.loc[v, rep].sum().values
    stk["p/e"] = stk["Close Price"]/stk["EPS"]
    return stk


def add_next_day_columns(stock):
    """
    Creates new Next Day columns in the stock dataframe.
    Parameters
    ----------
    stock : dataframe
    Returns
    -------
    stock : dataframe
        updated dataframe with Next Day columns.
    """

    new_columns = ["Next Day Open Price", "Next Day High Price",
                   "Next Day Low Price", "Next Day Close Price"]
    columns = ["Open Price", "High Price", "Low Price", "Close Price"]
    stock[new_columns] = pd.DataFrame([[0, 0, 0, 0]], index=stock.index)
    stock[new_columns] = stock[columns].shift(1)
    return stock


direct_columns = ['Open Price', 'High Price', 'Low Price', 'Close Price', 'Next Day Open Price', 'Next Day High Price', 'Next Day Low Price', 'Next Day Close Price', 'WAP',
                  'No.of Shares', 'No. of Trades', 'Total Turnover (Rs.)', 'Deliverable Quantity', '% Deli. Qty to Traded Qty', 'Spread High-Low', 'Spread Close-Open', 'Alpha', 'Beta']
growth_direct_rate_columns = [col + " GR" for col in direct_columns]


def find_gain_loss(stock):
    """
    Creates new growth rate columns in the stock dataframe.
    Growth rate = (X-Y)/Y
    X = value of today
    Y = value of the previous trading day
    Parameters
    ----------
    stock : dataframe
    Returns
    -------
    stock : dataframe
        updated dataframe with newly created columns.
    """
    direct_columns = ['Open Price', 'High Price', 'Low Price', 'Close Price', 'Next Day Open Price', 'Next Day High Price', 'Next Day Low Price', 'Next Day Close Price', 'WAP',
                      'No.of Shares', 'No. of Trades', 'Total Turnover (Rs.)', 'Deliverable Quantity', '% Deli. Qty to Traded Qty', 'Spread High-Low', 'Spread Close-Open', 'Alpha', 'Beta']
    growth_direct_rate_columns = [col + " GR" for col in direct_columns]

    # stock[direct_columns] = stock[direct_columns].apply(
    #     pd.to_numeric, errors="coerce")
    stock[direct_columns] = (stock[direct_columns].astype(
        str)).apply(pd.to_numeric, errors='coerce')
    stock[growth_direct_rate_columns] = pd.DataFrame(
        [[0]*len(growth_direct_rate_columns)], index=stock.index)
    today = stock[direct_columns]
    previous = stock[direct_columns].shift(1)
    stock[growth_direct_rate_columns] = (today-previous)/previous
    return stock


def sequential_increase(stock):
    """
    Creates new Sequential Increase column in the stock dataframe.
    Parameters
    ----------
    stock : dataframe
    Returns
    -------
    stock : dataframe
        updated dataframe with newly created column.
    """

    stock["Sequential Increase"] = ""
    c = 0
    stock.at[stock.shape[0]-2, "Sequential Increase"] = 0
    stock.at[stock.shape[0]-1, "Sequential Increase"] = 0
    for i in range(stock.shape[0]-2, 0, -1):
        if stock.at[i, "Close Price"] > stock.at[i+1, "Close Price"]:
            c += 1
            stock.at[i-1, "Sequential Increase"] = c
        else:
            stock.at[i-1, "Sequential Increase"] = 0
            c = 0
    return stock


def sequential_decrease(stock):
    """
    Creates new Sequential Decrease column in the stock dataframe.
    Parameters
    ----------
    stock : dataframe
    Returns
    -------
    stock : dataframe
        updated dataframe with newly created column.
    """

    stock["Sequential Decrease"] = 0
    c = 1
    stock.at[stock.shape[0]-2, "Sequential Decrease"] = 0
    stock.at[stock.shape[0]-1, "Sequential Decrease"] = 0
    for i in range(stock.shape[0]-2, 0, -1):
        if stock.at[i, "Close Price"] < stock.at[i+1, "Close Price"]:
            stock.at[i-1, "Sequential Decrease"] = c
            c += 1
        else:
            stock.at[i-1, "Sequential Decrease"] = 0
            c = 1
    return stock


def sequential_increase_percentage(stock):
    """
    Creates new Sequential Increase % column in the stock dataframe.
    Parameters
    ----------
    stock : dataframe
    Returns
    -------
    stock : dataframe
        updated dataframe with newly created column.
    """

    stock["Sequential Increase %"] = ""
    for i in range(stock.shape[0]-2):
        if stock.at[i, "Sequential Increase"] != 0:
            inc = stock.at[i, "Sequential Increase"]
        else:
            inc = 1
        fr = stock.at[i+1, "Close Price"]
        to = stock.at[i+1+inc, "Close Price"]
        stock.at[i, "Sequential Increase %"] = (fr - to) / to
    stock.at[stock.shape[0]-2, "Sequential Increase %"] = 0
    stock.at[stock.shape[0]-1, "Sequential Increase %"] = 0
    return stock


def sequential_decrease_percentage(stock):
    """
    Creates new Sequential Decrease % column in the stock dataframe.
    Parameters
    ----------
    stock : dataframe
    Returns
    -------
    stock : dataframe
        updated dataframe with newly created column.
    """

    stock["Sequential Decrease %"] = ""
    for i in range(stock.shape[0]-2):
        if stock.at[i, "Sequential Decrease"] != 0:
            inc = stock.at[i, "Sequential Decrease"]
        else:
            inc = 1
        fr = stock.at[i+1, "Close Price"]
        to = stock.at[i+1+inc, "Close Price"]
        stock.at[i, "Sequential Decrease %"] = (to - fr) / fr
    stock.at[stock.shape[0]-2, "Sequential Decrease %"] = 0
    stock.at[stock.shape[0]-1, "Sequential Decrease %"] = 0
    return stock


def max_min_avg_of_sequential_data(stock):
    """
    Creates lists for increasing and decreasing % for Sequential Increase and Sequential Decrease columns dataframe.
    Parameters
    ----------
    stock : dataframe
    Returns
    -------
    seq_inc_list : list
    seq_dec_list : list
    """
    index_start = stock.first_valid_index()
    seq_inc_days = stock.at[index_start, "Sequential Increase"]
    seq_dec_days = stock.at[index_start, "Sequential Decrease"]
    seq_inc_list = [0]
    seq_dec_list = [0]
    for i in range(index_start, stock.shape[0]+index_start):
        if stock.at[i, "Sequential Increase"] == seq_inc_days:
            seq_inc_list.append(stock.at[i, "Sequential Increase %"])
        if stock.at[i, "Sequential Decrease"] == seq_dec_days:
            seq_dec_list.append(stock.at[i, "Sequential Decrease %"])
    seq_inc_list = [i for i in seq_inc_list if i != 0 and i]
    seq_dec_list = [i for i in seq_dec_list if i != 0 and i]
    return seq_inc_list, seq_dec_list


def sequential_increase_decrease(stock):
    """
    Creates new max, min, avg columns for Sequential Increase and Sequential Decrease columns 
    with 90, 180, 365 bands in stock dataframe.
    Parameters
    ----------
    stock : dataframe
    Returns
    -------
    stock : dataframe
        updated dataframe with newly created column.
    """
    bands = [90, 180, 365]
    for b in bands:
        bcols = ["Max Inc % in "+str(b)+" days", "Max Dec % in "+str(b)+" days", "Min Inc % in "+str(
            b)+" days", "Min Dec % in "+str(b)+" days", "Avg Inc % in "+str(b)+" days", "Avg Dec % in "+str(b)+" days"]
        stock[bcols] = pd.DataFrame([[0]*len(bcols)], index=stock.index)
        for i in range(stock.shape[0]):
            s = i+1
            specific_bands = stock.iloc[-(s):-(s+b+1):-1]
            specific_bands.sort_index(inplace=True)
            seq_inc_list, seq_dec_list = max_min_avg_of_sequential_data(
                specific_bands)
            try:
                stock.loc[specific_bands.index, bcols] = [max(seq_inc_list), max(seq_dec_list), min(
                    seq_inc_list), min(seq_dec_list), np.mean(seq_inc_list), np.mean(seq_dec_list)]
            except:
                traceback.print_exc()
    return stock


cols = ["Revenue", "Dividend Value", "Income",
        "Expenditure", "Net Profit", "EPS"]


def generate_dictionary_for_quarterwise_data(stock, columnName):
    """
    generates a dictionary for the given column quaterwise.
    Parameters
    ----------
    stock : dataframe
    columnName : string
    Returns
    -------
    result : dictionary
    """
    result = {}
    stock.Date = pd.to_datetime(stock.Date)
    for index, row in stock.iterrows():
        try:
            q = (row.Date.month-1)//3 + 1
            year = row.Date.year
            month = row.Date.month
            res = result.get(year, {})
            # amount = re.findall(r"\d+.?\d*",row["Revenue"])[0]
            amount = row[columnName]
            q = "1q" if 1 <= month <= 3 else "2q" if 4 <= month <= 6 else "3q" if 6 <= month <= 9 else "4q"
            val = res.get(q, [])
            val.append(float(amount))
            res[q] = val
            result[year] = res
        except:
            traceback.print_exc()

    return result


def generate_dictionary_for_quarterwise_growthrate_data(data):
    """
    generates a dictionary for quater wise growth rate.
    Parameters
    ----------
    data : dictionary
    columnName : string
    Returns
    -------
    gr_dic : dictionary
    """
    gr_dic = {}
    keys = list(data.keys())
    array = [''] * (len(keys)*4)
    array_index = 0
    for key in data:
        lists = data.get(key)
        array_index += 4 - len(lists.keys())
        for lis in lists:
            if math.isnan(lists.get(lis)[0]):
                array[array_index] = ''
            else:
                array[array_index] = lists.get(lis)[0]
            array_index = array_index + 1
    if (array.count('')) > ((len(keys) * 4) / 2):
        return gr_dic

    for i in range(4, len(keys)*4, 4):
        res = [array[i], array[i+1], array[i+2], array[i+3]]
        avg = np.mean(list(filter(lambda i: isinstance(i, float), res)))
        if np.isnan(avg):
            pass
        else:
            array[i] = avg

    gr_array = [''] * (len(keys)*4)
    for i in range(0, len(keys)*4-1):
        x = array[i]
        y = array[i+1]
        if x == '' and y == '':
            continue
        if y == '' or y == 0:
            continue
        if x == '':
            gr_array[i] = 1
        else:
            gr_array[i] = (x - y) / y
    index = 0
    for key in data:
        gr_dic[key] = [gr_array[index], gr_array[index+1],
                       gr_array[index+2], gr_array[index+3]]
        index = index + 4
    return gr_dic


def update_growthrate_for_quarterwise_data(gr_dic, stock, columnName):
    """
    generates a dictionary for the given column quaterwise.
    Parameters
    ----------
    gr_dic : dictionary
    stock : dataframe
    columnName : string
    Returns
    --------
    stock : dataframe
    """
    for i in range(0, stock.shape[0]-1):
        date = stock.at[i, "Date"]
        q = int((date.month-1)//3)
        year = date.year
        if year in gr_dic.keys():
            stock.at[i, columnName+" GR"] = gr_dic.get(
                year)[q] if isinstance(gr_dic.get(year)[q], float) else 0
    return stock


def quarter_wise_growthrate(stock, columnName):
    """
    Creates new Growth Rate column in the stock dataframe.
    Parameters
    ----------
    stock : dataframe
    columnName : string
    Returns
    --------
    stock : dataframe
    """
    dic = generate_dictionary_for_quarterwise_data(stock, columnName)
    gr_dic = generate_dictionary_for_quarterwise_growthrate_data(dic)
    stock[columnName + ' GR'] = ''
    if gr_dic == {}:
        return stock
    else:
        stock = update_growthrate_for_quarterwise_data(
            gr_dic, stock, columnName)
    return stock


def close_price_as_percent_of_LV_HV_BA(stock):
    """
    Creates new growth rate columns in the stock dataframe.
    For Close Price as% Lowest Value, close price as% Highest Value, close price as% Band Area
    for 7, 30, 90, 180, 365 bands
    Close Price as % of Lowest Value = Close Price of that day/min close price in the band
    Close Price as % of Highest Value = Close Price of that day/max close price in the band
    Close Price as % of Band Area = Close Price of that day / (max-min close price in the band)
    Parameters
    ----------
    stock : dataframe
    Returns
    -------
    stock : dataframe
        updated dataframe with newly created columns.
    """

    bands = [7, 30, 90, 180, 365]
    for b in bands:
        bcols = ["CP % LV "+str(b)+" days", "CP % HV " +
                 str(b)+" days", "CP % BA "+str(b)+" days"]
        stock[bcols] = pd.DataFrame([[0]*len(bcols)], index=stock.index)
        for i in range(stock.shape[0]):
            s = i+1
            specific_bands = stock.iloc[-(s):-(s+b+1):-1]
            low = specific_bands["Close Price"].min()
            high = specific_bands["Close Price"].max()
            today = stock.iloc[-(s)]["Close Price"]
            stock.loc[specific_bands.index, bcols] = [
                today/low, today/high, today/(high-low)]
    return stock


def create_new_LB_UB(stock):
    """
    Creates new growth rate columns in the stock dataframe.
    Previous and Next ,Lower Band, Upper Band for 
    for 30,90,180,360,720,1080 days
    Lower Lower = Close Price of that day/min close price in the band
    Upper Band = Close Price of that day/max close price in the band
    Parameters
    ----------
    stock : dataframe
    Returns
    -------
    stock : dataframe
        updated dataframe with newly created columns.
    """

    bands = [30, 60, 90, 180, 360, 720, 1080]
    for b in bands:
        pcols = ["Previous " + str(b) + " days LB",
                 "Previous " + str(b) + " days UB"]
        stock[pcols] = pd.DataFrame([[0]*len(pcols)], index=stock.index)
        for index, row in stock.iterrows():
            start = row['Date'] - datetime.timedelta(days=1)
            end = start - datetime.timedelta(days=b)
            specific_dates = stock[stock.Date.between(end, start)]
            low = specific_dates["Close Price"].min()
            high = specific_dates["Close Price"].max()
            today = row["Close Price"]
            stock.loc[index, pcols] = [low/today, high/today]

    bands = [30, 60, 90, 180, 360, 720, 1080]
    for b in bands:
        ncols = ["Next " + str(b) + " days LB", "Next " + str(b) + " days UB"]
        stock[ncols] = pd.DataFrame([[0]*len(ncols)], index=stock.index)
        for index, row in stock.iterrows():
            start = row['Date'] + datetime.timedelta(days=1)
            end = start + datetime.timedelta(days=b)
            specific_dates = stock[stock.Date.between(start, end)]
            low = specific_dates["Close Price"].min()
            high = specific_dates["Close Price"].max()
            today = row["Close Price"]
            stock.loc[index, ncols] = [low/today, high/today]
    return stock

def perform_operation(security_code):
    try:
        security_code = str(security_code)
        print(security_code)
        index_df = pd.read_csv(os.path.join(path,"Index.csv"))
        corporate_df = pd.read_csv(os.path.join(path,"CorporateActions/"+security_code+".csv"))
        revenue_df = pd.read_csv(os.path.join(path,"Revenue/"+security_code+".csv"))
        stock_df = pd.read_csv(os.path.join(path,"Stock/"+security_code+".csv"))
        stock_df,index_df = cleaning(stock_df,index_df)
        stock_df = apply_corporate_actions(stock_df,corporate_df)
        stock_df = calculate_beta(stock_df,index_df)
        stock_df = add_risk_free_column(stock_df)
        stock_df = calculate_alpha(stock_df,index_df)
        stock_df = create_lower_upper_bands(stock_df)
        stock_df = create_new_LB_UB(stock_df)
        stock_df = create_eps_pe_ratio_revenue_income_expenditure_net_profit(revenue_df,stock_df)
        stock_df = add_next_day_columns(stock_df)
        stock_df[direct_columns] = stock_df[direct_columns].apply(pd.to_numeric,errors="coerce")
        stock_df = find_gain_loss(stock_df)
        stock_df = sequential_increase(stock_df)
        stock_df = sequential_decrease(stock_df)
        stock_df = sequential_increase_percentage(stock_df)
        stock_df = sequential_decrease_percentage(stock_df)
        stock_df = sequential_increase_decrease(stock_df)
        for col in cols:
            try:
                stock_df = quarter_wise_growthrate(stock_df, col)
            except Exception as e:
                traceback.print_exc()
        stock_df = close_price_as_percent_of_LV_HV_BA(stock_df)
        stock_df.to_csv(os.path.join(path,"GRStock/"+"gr"+str(security_code)+".csv"),index=None)
    except :
        traceback.print_exc()
        
