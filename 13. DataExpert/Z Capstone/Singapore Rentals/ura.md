Logo
Search
Introduction
Authentication
Car Park
Private Residential Property
Private Residential Property Transactions
Private Non-Landed Residential Properties Median Rentals by Name
Private Residential Properties Rental Contract
Private Residential Property Units Sold by Developers
Private Residential Projects in the Pipeline
Planning Decisions
Approved Use
Sign Up for an Access Key
Introduction
URA publishes URA related data for public use and is available for download for the creation, development and testing of innovative applications by third party.

You can register for an account here. After activation of your account, you will receive an email with an access key from which you can generate a token for access to the API.

Once the token is generated, users are allowed to access the URA data service using the following way.

Authentication
Get Token
To get a token, use this code:

curl "https://eservice.ura.gov.sg/uraDataService/insertNewToken/v1"
  -H "AccessKey: accesskey"
Make sure to replace accesskey with your access key.

The above request returns JSON structured like this:

{
  "Result": "42-0xjxf--aYa3J@@bH4mq5aZga-MMd6Vc5XfK74d464Ayc4@AU8UP5h5TCCqt3ccV@0N+0874-j6d59dpC3bfscqPP3P252TYj",
  "Status": "Success",
  "Message": ""
}
This data service will return a token to be used for the day’s access to the API.

Update Frequency: NA

HTTP Request
GET https://eservice.ura.gov.sg/uraDataService/insertNewToken/v1

HTTP Request Header
Header	Mandatory	Description
AccessKey	Yes	The access key included in the email upon successful activation of account.
HTTP Response
Key	Description
Result	The token to be used for the day to access to the other data services.
Car Park
Car Park Available Lots
To get a list of available car park lots, use this code:

curl "https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=Car_Park_Availability"
  -H "AccessKey: accesskey"
  -H "Token: token"
Make sure to replace accesskey with your access key.

Make sure to replace token with the day's token.

The above request returns JSON structured like this:

{
  "Status": "Success",
  "Message": "",
  "Result": [{
      "lotsAvailable": "0",
      "lotType": "M",
      "carparkNo": "N0006",
      "geometries": [{
        "coordinates": "28956.4609, 29088.2522"
      }]
    },
    {
      "lotsAvailable": "2",
      "lotType": "M",
      "carparkNo": "S0108",
      "geometries": [{
        "coordinates": "29930.895, 33440.7746"
      }]
    }
  ]
}
This data service will return the list of URA car park available lots in JSON format.

Update Frequency: Every 3 to 5 mins

HTTP Request
GET https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=Car_Park_Availability

HTTP Request Header
Header	Mandatory	Description
AccessKey	Yes	The access key included in the email upon successful activation of account.
Token	Yes	The token generated from the request token service for daily data request.
HTTP Response
Key	Description
carparkNo	5 digit car park code
lotType	The type of vehicle lots for the car park
C - Car
M - Motorcycle
H - Heavy Vehicle
lotsAvailable	Remaining free lots
geometries	An array of URA short term car park’s coordinates in SVY21 format.
coordinates	A set of URA short term car park coordinates Note: there may be more than 1 set of coordinates if the car park belongs to an on-street.
Car Park List and Rates
To get a list of URA car park details and rates, use this code:

curl "https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=Car_Park_Details"
  -H "AccessKey: accesskey"
  -H "Token: token"
The above command returns JSON structured like this:

{
  "Status": "Success",
  "Message": "",
  "Result": [{
      "weekdayMin": "30mins",
      "ppName": "ALIWAL STREET",
      "endTime": "05.00 PM",
      "weekdayRate": "$0.50",
      "startTime": "08.30 AM",
      "ppCode": "A0004",
      "sunPHRate": "$0.50",
      "satdayMin": "30 mins",
      "sunPHMin": "30 mins",
      "parkingSystem": "C",
      "parkCapacity": 69,
      "vehCat": "Car",
      "satdayRate": "$0.50",
      "geometries": [{
          "coordinates": "31045.6165, 31694.0055"
        },
        {
          "coordinates": "31126.0755, 31564.9876"
        }
      ]
    },
    {
      "weekdayMin": "30 mins",
      "ppName": "ALIWAL STREET ",
      "endTime": "10.00 PM",
      "weekdayRate": "$0.50",
      "startTime": "05.00 PM",
      "ppCode": "A0004",
      "sunPHRate": "$0.50",
      "satdayMin": "30 mins",
      "sunPHMin": "30 mins",
      "parkingSystem": "C",
      "parkCapacity": 69,
      "vehCat": "Car",
      "satdayRate": "$0.50",
      "geometries": [{
          "coordinates": "31045.6165, 31694.0055"
        },
        {
          "coordinates": "31126.0755, 31564.9876"
        }
      ]
    }
  ]
}
This data service will return the list of URA car park details and rates in the JSON format.

Update Frequency: Daily

HTTP Request
GET https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=Car_Park_Details

HTTP Request Header
Header	Mandatory	Description
AccessKey	Yes	The access key included in the email upon successful activation of account.
Token	Yes	The token generated from the request token service for daily data request.
HTTP Response
Key	Description
ppCode	5 digit car park code
ppName	Carpark name
vehCat	Vehicle Category
C - Car
M - Motorcycle
H - Heavy Vehicle
startTime	Effective start time of parking rate
endTime	Effective end time of parking rate
weekdayRate	Parking rate on weekday. Note that prices are in dollars ($)
weekdayMin	The maximum duration of the rate. Note that is this for Weekday. Value 30 mins would imply e.g. $0.65 per 30 min
satdayRate	Parking rate on Saturday
satdayMin	The maximum duration of the rate. Note that is this for Saturday. Value 30 mins would imply e.g. $0.65 per 30 min.
sunPHRate	Parking rate on Sunday and public holiday
sunPHMin	The maximum duration of the rate. Note that is this for Sunday. Value 30 mins would imply e.g. $0.65 per 30 min.
remarks	Remarks for the car park
parkingSystem	The type of parking system the car park is in use
C - Coupon Parking System
B - Electronic Parking System
parkCapacity	Number of carpark lots
geometries	An array of URA short term car park’s coordinates in SVY21 format
coordinates	A set of URA short term car park coordinates Note: there may be more than 1 set of coordinates if the car park belongs to an on-street.
Season Car Park List and Rates
To get a list of available car park lots, use this code:

curl "https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=Car_Park_Availability"
  -H "AccessKey: accesskey"
  -H "Token: token"
Make sure to replace accesskey with your access key.

Make sure to replace token with the day's token.

The above request returns JSON structured like this:

{
  "Status": "Success",
  "Message": "",
  "Result": [{
      "lotsAvailable": "0",
      "lotType": "M",
      "carparkNo": "N0006",
      "geometries": [{
        "coordinates": "28956.4609, 29088.2522"
      }]
    },
    {
      "lotsAvailable": "2",
      "lotType": "M",
      "carparkNo": "S0108",
      "geometries": [{
        "coordinates": "29930.895, 33440.7746"
      }]
    }
  ]
}
This data service will return the list of URA season car park details and rates available for application in JSON format.

Update Frequency: Daily

HTTP Request
GET https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=Season_Car_Park_Details

HTTP Request Header
Header	Mandatory	Description
AccessKey	Yes	The access key included in the email upon successful activation of account.
Token	Yes	The token generated from the request token service for daily data request.
HTTP Response
Key	Description
ppCode	5 digit car park code. Note: ppCode starting with ‘G’ represents group parking lots.
ppName	Carpark name
vehCat	Vehicle Category
C - Car
M - Motorcycle
H - Heavy Vehicle
parkingHrs	Season parking hours
ticketType	Type of season tickets
monthlyRate	Parking rate
geometries	An array of URA season car park’s coordinates in SVY21 format.
coordinates	A set of season car park coordinates Note: there may be more than 1 set of coordinates if the car park belongs to a group car park beginning with the prefix of ‘G’.
Private Residential Property
Private Residential Property Transactions
To get a list of private property transactions for the past 5 years, use this code:

curl "https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=PMI_Resi_Transaction&batch=1"
  -H "AccessKey: accesskey"
  -H "Token: token"
Make sure to replace accesskey with your access key.

Make sure to replace token with the day's token.

The above request returns JSON structured like this:

{
  "Result": [{
    "project": "TURQUOISE",
    "marketSegment": "CCR",
    "transaction": [{
        "contractDate": "0715",
        "area": "203",
        "price": "2900000",
        "propertyType": "Condominium",
        "typeOfArea": "Strata",
        "tenure": "99 yrs lease commencing from 2007",
        "floorRange": "01-05",
        "typeOfSale": "3",
        "district": "04",
        "noOfUnits": "1"
      },
      {
        "contractDate": "0116",
        "area": "200",
        "price": "3014200",
        "propertyType": "Condominium",
        "typeOfArea": "Strata",
        "tenure": "99 yrs lease commencing from 2007",
        "floorRange": "01-05",
        "typeOfSale": "3",
        "district": "04",
        "noOfUnits": "1"
      }
    ],
    "street": "COVE DRIVE",
    "y": "24997.821719180001",
    "x": "28392.530515570001"
  }],
  "Status": "Success"
}
This data service will return past 5 years of private residential property transaction records in JSON format. As transaction records > 5 years ago could be modified/aborted, we would advise to refresh your database on a daily basis and just retain the latest 5 years record for better accuracy.

Update Frequency: End of day of every Tuesday and Friday

HTTP Request
GET https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=PMI_Resi_Transaction&batch=1

HTTP Request Header
Header	Mandatory	Description
AccessKey	Yes	The access key included in the email upon successful activation of account.
Token	Yes	The token generated from the request token service for daily data request.
HTTP Request URL Parameters
Parameter	Mandatory	Description
Batch	Yes	Data are available for download in 4 batches.
1
2
3
4
They are split by postal districts e.g. batch 1 is for postal district 01 to 07, batch 2 is for postal district 08 to 14 etc. To download for batch 1, pass in the value 1.
HTTP Response
Key	Description
project	The name of the project
street	The street name that the project is on.
marketSegment	The market segment that the property falls in.
CCR – Core Central Region
RCR – Rest of Central Region
OCR – Outside Central Region
x	The x coordinates of the address of the property in SVY21 format. Important: This is the location of the property and does not represent the location of the transacted unit.
y	The y coordinates of the address of the property in SVY21 format. Important: This is the location of the property and does not represent the location of the transacted unit.
transaction	An array of transactions for this property
    propertyType	The property type of the transacted property. Note that there are properties with a mixture of property types.
Strata Detached
Strata Semidetached
Strata Terrace
Detached
Semi-detached
Terrace
Apartment
Condominium
Executive Condominium
    district	The postal district that the transacted property falls in. Note that there are properties that fall across multiple postal district.
    tenure	The tenure of the transacted property. Note that there are properties that have units with multiple tenures.
Freehold
xx yrs lease commencing from yyyy
    typeOfSale	The type of sale
1 – New Sale
2 – Sub Sale
3 – Resale
    noOfUnits	The number of units in this transaction. The value for New Sale will always be 1. The value for Resale or Sub Sale could be greater than 1 depending on the number of units lodged for the caveat.
    price	The transacted price nettPrice
    nettPrice	The nett transacted price, excluding discounts if any. This field is only applicable for New Sale where discounts were given.
    area	The land/floor area of the transacted unit in square metre.
    typeOfArea	The type of area of the transacted unit.
Strata
Land
Unknown
    floorRange	The floor range that the transacted unit falls within.
-
B1-B5
B6-B10
01-05
06-10
...
    contractDate	The data of sale for New Sale records or option exercised date for Resale and Sub Sale records. Field is in format of mmyy e.g. 1215 represents Dec 2015.
Private Non-Landed Residential Properties Median Rentals by Name
To get a list of median rentals of private non-landed residential properties for the past 3 years, use this code:

curl "https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=PMI_Resi_Rental_Median"
  -H "AccessKey: accesskey"
  -H "Token: token"
Make sure to replace accesskey with your access key.

Make sure to replace token with the day's token.

The above request returns JSON structured like this:

{
  "Result": [{
      "project": "MERAWOODS",
      "street": "HILLVIEW AVENUE",
      "rentalMedian": [{
          "median": 2.5,
          "psf25": 2.32,
          "psf75": 2.6,
          "district": "23",
          "refPeriod": "2014Q2"
        },
        {
          "median": 2.48,
          "psf25": 2.16,
          "psf75": 2.55,
          "district": "23",
          "refPeriod": "2014Q3"
        },
        {
          "median": 2.45,
          "psf25": 2.29,
          "psf75": 2.8,
          "district": "23",
          "refPeriod": "2012Q1"
        }
      ],
      "y": "37575.873911829997",
      "x": "19822.860634660001"
    },
    {
      "project": "ELLIOT AT THE EAST COAST",
      "street": "ELLIOT ROAD",
      "rentalMedian": [{
          "median": 3.32,
          "psf25": 2.8,
          "psf75": 3.46,
          "district": "15",
          "refPeriod": "2012Q3"
        },
        {
          "median": 2.92,
          "psf25": 2.63,
          "psf75": 3.45,
          "district": "15",
          "refPeriod": "2014Q2"
        },
        {
          "median": 3.19,
          "psf25": 2.79,
          "psf75": 3.46,
          "district": "15",
          "refPeriod": "2012Q2"
        }
      ],
      "y": "32635.6331629",
      "x": "38853.473729029998"
    }
  ],
  "Status": "Success"
}
This data service will return past 3 years of median rentals of private non-landed residential properties with at least 10 rental contracts for the reference period in JSON format.

Update Frequency: End of day of every 4th Friday of January, April, July and October. If it is a public holiday, the data will be updated on the following working day.

HTTP Request
GET https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=PMI_Resi_Rental_Median

HTTP Request Header
Header	Mandatory	Description
AccessKey	Yes	The access key included in the email upon successful activation of account.
Token	Yes	The token generated from the request token service for daily data request.
HTTP Response
Key	Description
project	The name of the project
street	The street name that the project is on.
x	The x coordinates of the address of the property in SVY21 format. Important: This is the location of the property and does not represent the location of the rented unit.
y	The y coordinates of the address of the property in SVY21 format. Important: This is the location of the property and does not represent the location of the rented unit.
rentalMedian	An array of median rentals for this property
    district	The postal district that the transacted property falls in.
01
02
03
04
...
28
    refPeriod	The reference period for the rental information. Field is in format of YYYYQQ e.g. 2011Q3 represents 2011 3rd quarter.
    psf25	The 25th percentile per square feet per month for the property for the reference period.
    median	The median per square feet per month for the property for the reference period.
    psf75	The 75th percentile per square feet per month for the property for the reference period.
Private Residential Properties Rental Contract
To get the rental contracts of private residential properties for the past 5 years, use this code:

curl "https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=PMI_Resi_Rental&refPeriod=14q1"
  -H "AccessKey: accesskey"
  -H "Token: token"
Make sure to replace accesskey with your access key.

Make sure to replace token with the day's token.

The above request returns JSON structured like this:

{
  "Result": [{
      "project": "THOMSON RISE ESTATE",
      "street": "JALAN BERJAYA",
      "rental": [{
        "leaseDate": "0314",
        "propertyType": "Detached House",
        "areaSqm": "150-200",
        "areaSqft": "1500-2000",
        "rent": 4300,
        "district": "20"
      }],
      "y": "37250.512899840002",
      "x": "29360.426817729999"
    },
    {
      "project": "THE ESPIRA",
      "street": "LORONG L TELOK KURAU",
      "rental": [{
          "leaseDate": "0314",
          "propertyType": "Non-landed Properties",
          "areaSqm": "100-110",
          "areaSqft": "1100-1200",
          "rent": 3100,
          "district": "15",
          "noOfBedRoom": "3"
        },
        {
          "leaseDate": "0314",
          "propertyType": "Non-landed Properties",
          "areaSqm": "50-60",
          "areaSqft": "500-600",
          "rent": 2400,
          "district": "15",
          "noOfBedRoom": "1"
        }
      ],
      "y": "32747.030532890001",
      "x": "37045.353209170002"
    }
  ],
  "Status": "Success"
}
This data service will return past 5 years of private residential properties with rental contracts submitted to IRAS for Stamp Duty assessment in JSON format. As the rental records > 5 years ago could be modified/aborted, we would advise to refresh your database on a monthly basis and just retain the latest 5 years record for better accuracy.

Update Frequency: End of day of every 15th of the month. If it is a public holiday, the data will be updated on the following working day.

HTTP Request
GET https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=PMI_Resi_Rental&refPeriod=14q1

HTTP Request Header
Header	Mandatory	Description
AccessKey	Yes	The access key included in the email upon successful activation of account.
Token	Yes	The token generated from the request token service for daily data request.
HTTP Request URL Parameters
Parameter	Mandatory	Description
refPeriod	Yes	Data are available for download by reference quarter. Field is in format of yyqq e.g. 14q1 represents 2014 1st quarter.
HTTP Response
Key	Description
project	The name of the project
street	The street name that the project is on.
x	The x coordinates of the address of the property in SVY21 format. Important: This is the location of the property and does not represent the location of the transacted unit.
y	The y coordinates of the address of the property in SVY21 format. Important: This is the location of the property and does not represent the location of the transacted unit.
rental	An array of rental contracts for this property
    propertyType	The property type of the transacted property. Note that there are properties with a mixture of property types.
Non-landed Properties
Detached House
Semi-Detached House
Terrace House
Executive Condominium
    district	The postal district that the transacted property falls in. Note that there are properties that fall across multiple postal district.
01
02
03
04
...
28
    noOfBedRoom	The number of bed rooms. Information is only available for non-landed property. Empty value for non-landed properties means that the information was not provided for this property.
    rent	The monthly rent.
    areaSqft	The floor area range of the rented property in square feet.
    areaSqm	The floor area range of the rented property in square metre.
    leaseDate	The lease commencement date of the rental. Field is in format of mmyy e.g. 0314 represents March 2014.
Private Residential Property Units Sold by Developers
To get a list of prices of completed and uncompleted private residential units and executive condominiums with pre-requisite for sale sold by develoeprs for the past 3 years, use this code:

curl "https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=PMI_Resi_Developer_Sales&refPeriod=0913"
  -H "AccessKey: accesskey"
  -H "Token: token"
Make sure to replace accesskey with your access key.

Make sure to replace token with the day's token.

The above request returns JSON structured like this:

{
  "Result": [{
      "project": "LUXUS HILLS",
      "marketSegment": "OCR",
      "developer": "Singapore United Estates Pte Ltd",
      "street": "YIO CHU KANG ROAD/ANG MO KIO AVENUE 5/SELETAR ROAD",
      "developerSales": [{
        "highestPrice": 0,
        "soldToDate": 90,
        "unitsAvail": 236,
        "medianPrice": 0,
        "soldInMonth": 0,
        "launchedToDate": 90,
        "lowestPrice": 0,
        "refPeriod": "0913",
        "launchedInMonth": 0
      }],
      "district": "28",
      "y": "40264.704801180002",
      "x": "32524.18989369"
    },
    {
      "project": "BLOSSOM RESIDENCES",
      "marketSegment": "OCR",
      "developer": "Grand Isle Holdings Pte Ltd",
      "street": "SEGAR ROAD",
      "developerSales": [{
        "highestPrice": 0,
        "soldToDate": 601,
        "unitsAvail": 602,
        "medianPrice": 0,
        "soldInMonth": 0,
        "launchedToDate": 602,
        "lowestPrice": 0,
        "refPeriod": "0913",
        "launchedInMonth": 0
      }],
      "district": "23"
    }
  ],
  "Status": "Success"
}
This data service will return past 3 years of prices of completed and uncompleted private residential units and executive condominiums with pre-requisite for sale sold by developers in JSON format.

Update Frequency: End of day of every 15th of the month. If it is a public holiday, the data will be updated on the following working day.

HTTP Request
GET https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=PMI_Resi_Developer_Sales&refPeriod=0913

HTTP Request Header
Header	Mandatory	Description
AccessKey	Yes	The access key included in the email upon successful activation of account.
Token	Yes	The token generated from the request token service for daily data request.
HTTP Request URL Parameters
Parameter	Mandatory	Description
refPeriod	Yes	Data are available for download by reference quarter. Field is in format of mmyy e.g. 0913 represents Sep 2013.
HTTP Response
Key	Description
project	The name of the project
propertyType	The property type of the project.
-
Landed/Non-Landed
Landed
Non-Landed
Exec Condo
Strata-Landed
Strata-Landed/Non-Landed
street	The street name that the project is on.
developer	The name of the developer of the project.
marketSegment	The market segment that the property falls in.
CCR – Core Central Region
RCR – Rest of Central Region
OCR – Outside Central Region
district	The postal district that the transacted property falls in.
01
02
03
04
...
28
x	The x coordinates of the address of the property in SVY21 format. Important: This is the location of the property and does not represent the location of the transacted unit.
y	The y coordinates of the address of the property in SVY21 format. Important: This is the location of the property and does not represent the location of the transacted unit.
developerSales	An array of developer sales transaction for this property
    refPeriod	The reference period for the transaction based on the option to purchase issued by developers to purchasers. Field is in format of mmyy e.g. 0913 represents Sep 2013.
    medianPrice	The median price per square feet of the transacted units for the reference period.
    lowestPrice	The lowest transacted price per square feet of the transacted units for the reference period.
    highestPrice	The highest transacted price per square feet of the transacted units for the reference period.
    unitsAvail	The total number of units in this project.
    launchedToDate	The number of units launched for sale to date.
    soldToDate	The number of units sold to date.
    launchedInMonth	The number of units launched for sale for the reference period.
    soldInMonth	The number of units sold for the reference period.
Private Residential Projects in the Pipeline
To get a list of project pipeline data for the latest quarter, use this code:

curl "https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=PMI_Resi_Pipeline"
  -H "AccessKey: accesskey"
  -H "Token: token"
Make sure to replace accesskey with your access key.

Make sure to replace token with the day's token.

The above request returns JSON structured like this:

{
  "Result": [{
      "noOfApartment": 0,
      "totalUnits": 27,
      "project": "ONE SURIN",
      "noOfTerrace": 27,
      "noOfCondo": 0,
      "noOfDetachedHouse": 0,
      "street": "SURIN AVENUE",
      "developerName": "Urban Lofts Pte Ltd",
      "noOfSemiDetached": 0,
      "expectedTOPYear": "na",
      "district": "19"
    },
    {
      "noOfApartment": 0,
      "totalUnits": 420,
      "project": "THE SKYWOODS",
      "noOfTerrace": 0,
      "noOfCondo": 420,
      "noOfDetachedHouse": 0,
      "street": "DAIRY FARM HEIGHTS",
      "developerName": "Bukit Timah Green Development Pte Ltd",
      "noOfSemiDetached": 0,
      "expectedTOPYear": "na",
      "district": "23"
    }
  ],
  "Status": "Success"
}
This data service will return the latest quarter of project pipeline data in JSON format.

Update Frequency: End of day of every 4th Friday of January, April, July and October. If it is a public holiday, the data will be updated on the following working day.

HTTP Request
GET https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=PMI_Resi_Pipeline

HTTP Request Header
Header	Mandatory	Description
AccessKey	Yes	The access key included in the email upon successful activation of account.
Token	Yes	The token generated from the request token service for daily data request.
HTTP Response
Key	Description
project	The name of the project
street	The street name that the project is on.
district	The postal district that the project falls in.
01
02
03
04
...
28
developer	The name of the developer of the project.
totalUnits	The total number of units in this project.
noOfDetachedHouse	The number of detached units in this project.
noOfSemiDetached	The number of semi-detached units in this project.
noOfTerrace	The number of terrace units in this project.
noOfApartment	The number of apartment units in this project.
noOfCondo	The number of condominium units in this project.
expectedTOPYear	The expected year of TOP. Values with ‘na’ is because developers has not given consent for this information to be released.
Planning Decisions
Planning Decisions
To get a list of information on Written Permission granted or rejected by URA, use this code:

curl "https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=Planning_Decision"
  -H "AccessKey: accesskey"
  -H "Token: token"
Make sure to replace accesskey with your access key.

Make sure to replace token with the day's token.

The above request returns JSON structured like this:

{
  "Status": "Success",
  "Message": "",
  "Result": [{
      "address": "230 VICTORIA STREET, BUGIS JUNCTION SHOPPING CENTRE",
      "submission_desc": "PROPOSED CHANGE USE OF PART OF BASEMENT 1 FROM OFFICE",
      "dr_id": "84089",
      "decision_date": "03/01/2011",
      "decision_type": "Written Permission",
      "appl_type": "Change of Use",
      "mkts_lotno": "TS13 01015C PT",
      "decision_no": "P291210-03B1-Z000",
      "submission_no": "291210-03B1-Z000",
      "delete_ind": "No"
    },
    {
      "address": "15 NASSIM ROAD,17 NASSIM ROAD",
      "submission_desc": "PROPOSED AMALGAMATION AND SUBDIVISION OF LAND INTO 2 PLOTS AND STRATA SUBDIVISION OF THE EXISTING 4 BLOCKS OF FLATS INTO 100 SEPARATE STRATA RESIDENTIAL UNITS ",
      "dr_id": "84070",
      "decision_date": "03/01/2011",
      "decision_type": "Written Permission",
      "appl_type": "Subdivision",
      "mkts_lotno": "TS25 01056M,TS25 01352L,TS25 01353C",
      "decision_no": "P061210-19E1-Z000",
      "submission_no": "061210-19E1-Z000"
    }
  ]
}
This data service will provide the information on Written Permission granted or rejected by URA in JSON format. The request can be requested by the year or by the last downloaded date.

Update Frequency: Daily

HTTP Request
GET https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=Planning_Decision

HTTP Request Header
Header	Mandatory	Description
AccessKey	Yes	The access key included in the email upon successful activation of account.
Token	Yes	The token generated from the request token service for daily data request.
HTTP Request URL Parameters
The service accepts either one but not both of the below parameters.

Parameter	Mandatory	Description
year	Yes	Data are available for download by year. Only records after year 2000 can be retrieved.
last_dnload_date	Yes	Data created, modified or deleted from this date till present. Date is in dd/mm/yyyy format and it cannot be more than one year ago.
 This is ok.

GET https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=Planning_Decision&year=2015
 So is this.

GET https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=Planning_Decision&last_dnload_date=15/06/2015
 But this is not ok.

GET https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=Planning_Decision&year=2015&last_dnload_date=15/06/2015
HTTP Response
Key	Description
dr_id	Unique key to identify the record
submission_no	Submission number
decision_no	Decision number
decision_date	Decision date in dd/mm/yyyy format
decision_type	Decision type
submission_desc	Submission or proposal description
address	Site address
mkts_lotno	MK/TS lot number
delete_ind	Indicate whether the record is deleted. This will be ‘Yes’ only when the input parameter is last_dnload_date.
Yes
No
Approved Use
Approved Residential Use
To check if an address is approved for residential use, use this code:

curl "https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=EAU_Appr_Resi_Use"
  -H "AccessKey: accesskey"
  -H "Token: token"
Make sure to replace accesskey with your access key.

Make sure to replace token with the day's token.

The above request returns JSON structured like this:

{
  "status": "Success",
  "Message": "",
  "isResiUse": "Y"
}
This data service will provide the information on whether an address is approved for Residential use.

Update Frequency: Quarterly

The following should be noted for this data service:

The data provided is only for private residential units. HDB developments and State Properties are not included.
Residential units within Shophouse developments are not included.
The data provided is updated quarterly based on completed developments that have obtained TOP. Developments that have not obtained TOP are not included in this service.
Residential properties that have been converted to non-residential uses on temporary basis are not included.
HTTP Request
GET https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=EAU_Appr_Resi_Use

HTTP Request Header
Header	Mandatory	Description
AccessKey	Yes	The access key included in the email upon successful activation of account.
Token	Yes	The token generated from the request token service for daily data request.
HTTP Request URL Parameters
Parameter	Mandatory	Description
blkHouseNo	Yes	The blk/house number of the address
street	Yes	The street of the address
storeyNo	No	The storey number of the address.
unitNo	No	The unit number of the address.
HTTP Response
Key	Description
isResiUse	Indicate whether the address is approved for Residential use. A response of ‘NA’ represents that either the record for the address is not available or the address is not approved for Residential use.
Y
NA
curl