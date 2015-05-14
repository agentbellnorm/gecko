
__author__ = 'Vishrut Reddi'
import datetime
from datetime import date
from pymongo import MongoClient
import json

'''
 ----------------------------------
| MONGO DB STRUCTURE FOR THE USER: |
 ----------------------------------

 Collection 1: User's current profit. (User_Profit)
 [Name: Profit]

 Collection 2: Stock's information of all the stock the user currently owns. (Company_Name, Company_Ticker, Unit_Stock_Price, Projected_Profit_Amt)
 [Name: StocksOwned]

 Colelction 3: (Article Information)

 Collection 4: (Article_Title, Pub_date, Score)
'''

class action:



	# Description: This method finds the minimum date difference between the current date and all the dates of
	#              published articles.
	#
	# @return minDate - minimum date difference between date of publication and current date (no. of days)
	def findMinDateDiff(symbol):
	  
		# Get curent datetime object
		curDateObj = datetime.datetime.now();

		# Get current datetime 
		curDate = date(curDateObj.year, curDateObj.month, curDateObj.day);

		db = action.getConnection();

		# Get list of article info
		articles = list(db.Article.find({'symbol': symbol}))

		# Temp Variables
		minDate = 0;
		firstRun = True;

		for doc in articles:

			dt = doc["date"]
			dt = dt.split('-')
			dt = date(int(dt[0]), int(dt[1]), int(dt[2]))

			if(firstRun):
				firstRun = False;
				# Get distance between current date and date of article publication
				minDate = (curDate - dt).days;


			diff = (curDate - dt).days;

			if(diff < minDate):
				minDate = diff;

		return minDate;


	# Description: This method would find the average score of all the latest articles in the database.
#
# @return avgScore - Average score of scored latest articles
	def findAvgScore(symbol):

		distance = action.findMinDateDiff(symbol);

		# Get curent datetime object
		curDateObj = datetime.datetime.now();

		# Get current datetime 
		curDate = date(curDateObj.year, curDateObj.month, curDateObj.day);

		db = action.getConnection();

		# Get list of article info
		articles = list(db.Article.find({'symbol': symbol}));

		listOfScores = []

		for doc in articles:

			dt = doc["date"]
			dt = dt.split('-')
			dt = date(int(dt[0]), int(dt[1]), int(dt[2]))
			if((curDate - dt).days == distance):
				listOfScores.append(doc["sentiment"]);

		numOfScores = len(listOfScores);

		# No Scores Found
		if(numOfScores == 0):
			return 0;

		else:
			totalSum = 0;

			for score in listOfScores:

				totalSum = totalSum + score;


			avgScore = float((totalSum)/(numOfScores));
				

		return avgScore;




	# Description: This method is used to establish the connection to the Gecko Database
	# (mongoDB) and get the instance of that connection. 
	#
	# @return db - Database Conneciton instance
	def getConnection():

		# Connect on the Default Host and Port
		client = MongoClient();

		# Connect to/ Create new DB for Gecko 
		db = client['GeckoDB'];
		
		# Return the databse connection instance
		return db;

		 

	# Description: This method is used to purchase a unit of stock of any company/organisation.
	#              All the information about the company and stock is provided so that it could be 
	#              inserted in the DB and user profit(s) could be updated. 
	#
	# @param name - Name of the Company
	# @param ticker - The Stock Identifier or Ticker of the Company
	# @param unitPrice - Current unit price of the Company's stock
	#
	# @return True/False
	def purchaseStock(name, ticker, unitPrice):

		# Get database connection instnace
		db = action.getConnection();

		# Get current user profit(s) from the DB
		# The colelction would always have a single document/tuple.
		curUserProfit = db.Profit.find_one()["User_Profit"];

		# Add another tuple to the currently purchased stock(s) table
		db.StocksOwned.insert({"Company_Name" : name, 'Company_Ticker' : ticker, "Unit_Stock_Price" : unitPrice});

		# Buy the stock i.e Deduct from profit(s)
		newUserProfit = float(curUserProfit) - float(unitPrice);

		# Update User Profit(s) 
		# Upsert parameter will insert instead of updating if the post is not found in the database.
		db.Profit.update({}, {"User_Profit": newUserProfit}, upsert=False)

		return True;


	# Description: This method is used to determine the action. The action could either be purchasing the stock
	#              or passing the oppurtunity. This method based on the regression equation determines whether the stock
	#              purchased now be profitable to the user after 2 units of time (2 days) or not. If it would be then the stock
	#			   is purchased, if not then the stock is not purchased.
	#
	# @param slope - The mathematical slope of the regression curve
	# @param intercept - The mathematical intercept of the regression curve
	# @param name - Name of the Company
	# @param ticker - The Stock Identifier or Ticker of the Company
	# @param unitPrice - Current unit price of the Company's stock
	#
	# @return True/False :: identifying if the stoc was purchased or not.
	def determineAction(slope, intercept, r_value, name, ticker, unitPrice):

		# Check if the regression line is increasing or not
		latestScore = action.findAvgScore(ticker)
		print("latest score: " + str(latestScore))
		if(r_value > 0.5 and latestScore > 0):

			# Now based on the current news article the stock prices are
			# suppose to increase in the coming time. Therefore we purchase now.
			action.purchaseStock(name, ticker, unitPrice);


			# Indicate Buying Action
			return True;


		# Stock prices are going DOWN and yelling TIMBER!
		else:

			# Do not buy, Sell Now or the user loses money in the time coming.
			
			# Indicate Skipping Action
			return False;




	# Description: This method is used to restart the system or start a new system. Everything would be 
	#              cleared from the DB if something exists for some previous session/user. This method would
	#			   restore the system to its initial form. 
	#
	# @return True/False
	def startNewSystem():

		# Get database connection instnace
		db = action.getConnection();

		# No news scores, No User Profit i.e Profit = $0, No user owned stock info
		db.drop_collection('StocksOwned')

		# Update User Profit(s) 
		# Upsert parameter will insert instead of updating if the post is not found in the database.
		db.Profit.update({}, {"User_Profit": 0}, upsert=False)

		return True;



	# Description: This method is used to sell a previously purchased stock by the user. The stock price at the 
	#              moment of selling is added to the profit and projected profit is compared with the real profit
	#			   to see how close the system's data was accurate.
	#
	# @param ticker - The Stock Identifier or Ticker of the Company
	#
	# @return True/False
	def sellStock(ticker):

		result = []
		result.append(db.StocksOwned.find_one({"Company_Ticker" : ticker}))

		# Checking if the stock the user is about to sell is  owned by him or not
		if (len(result) > 0):

			# Get the original price the stock was purchased for by the user
			purchasePrice = db.StocksOwned.find_one({"Company_Ticker" : ticker})["Unit_Stock_Price"]; 

			# Ben's Function
			# Provides with current day's unit stock price for the provided company ticker
			sellingPrice = get_current_info([ticker])["Open"];

			# Store the real profit the user earned
			realProfit = sellingPrice - purchasePrice;

			# Get the projected profit the system originally estimated
			projectedProfit = db.StocksOwned.find_one({"Company_Ticker" : ticker})["Projected_Profit_Amt"]; 

			# The higher the number the lower the system efficiency.
			invertedSystemEfficiency = abs(projectedProfit - realProfit);

			# print('Inverted System Efficiency: ' + systemEfficiency);

			# Get current user profit(s) from the DB
			curUserProfit = db.Profit.find_one()["User_Profit"];

			# Calculate New User Profit, after selling the stock
			newUserProfit = curUserProfit + sellingPrice;

			# Update User Profit(s) 
			# Upsert parameter will insert instead of updating if the post is not found in the database.
			db.Profit.update({}, {"User_Profit": newUserProfit}, upsert=False)

			# Delete the stock details as it no longer exists
			db.StocksOwned.remove({"Company_Ticker" : ticker}); 

			return True;

		# The Stock User wants to sell does not exist in the Database
		else:
			return False;






