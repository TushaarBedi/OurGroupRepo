# Dependencies
import requests
import json
import pandas as pd
import numpy as np
# Google developer API key
from config import gkey
from gmplot import gmplot
import textwrap

#http://clt-charlotte.opendata.arcgis.com/datasets/36b534fc414640fa843fc780f6d9aaf5_4.geojson
#Incident Data
url4 = "http://clt-charlotte.opendata.arcgis.com/datasets/36b534fc414640fa843fc780f6d9aaf5_4.geojson"
response4 = requests.get(url4)
df_incident = pd.DataFrame(response4.json()['features'])
arr4 = []
for b in df_incident["properties"]:
    arr4.append(b)
df_incident = pd.DataFrame(arr4)

#This drops an incident that is missing a latitude or a longitude
df_incident = df_incident.dropna(axis=0, subset=['Latitude', 'Longitude'],how='any')
df_incident=df_incident.reset_index(drop=True)

#Start user interaction
print("Let's find out if any CMPD officer involved shootings have occured near you!")

#If they are local, we will just inset Charlotte, NC into the address to reduce user error.
#Most users should be local
local=input("Is the address you are searching for in Charlotte, NC? Y/N ")
bad_input=True
while bad_input:
    local=local.lower()
    if local[0]=="n":
        local="n"
        bad_input=False
    elif local[0]=="y":
        local="y"
        bad_input=False
    else:
        local=input("Sorry. I did not understand your answer.\nIs the address you are searching for in Charlotte? Enter Y or N: ")

#Grab the street address from the user
is_number=False
print("I will ask you for the address--number first, then the street.")
#This loop will check to see if they are entering the address number
while is_number==False:
    add_number=input("Please enter the address number for the location you are searching on: ")
    if add_number.isdigit():
        is_number=True
    else:
        print("Oh no! Try again. Only the numbers, please.")
print("Great! Thanks.")
add_street=input("Now enter in the street name like this: 'Michie Ct'. \nNow you try: ")

#We already found out if they are local, so now we generate the city and state based on that (automatic for local, user-input for nonlocal)
if local=="y":
    city="Charlotte"
    state="NC"
else:
    city=input("Please enter your US city: ")
    bad_input=True
    while bad_input:
        state=input("Please enter you two digit state (example: NC, VT, VA, etc):")
        if len(state)!=2:
            print("Remember, only the two digit postal code for your state, like CA or ME.")
        else:
            bad_input=False
#geocoding does not want spaces, so we replace them with plus signs in the city
city=city.replace(" ","+")
#again, the street name cannot have spaces
address=add_number+"+"+add_street+",+"+city+",+"+state
address=address.replace(" ","+")

#Now we use google to find the person's search address
base_url="https://maps.googleapis.com/maps/api/geocode/json?address="
key_base="&key="+gkey

response=requests.get(base_url+address+key_base,"Problem").json()

if response =="Problem":
        
    nearest_lat=float('nan')
    nearest_lng=float('nan')

else:
    try:
        nearest_lat=response["results"][0]["geometry"]["location"]["lat"]
        nearest_lng=response["results"][0]["geometry"]["location"]["lng"]
    except:
        nearest_lat=float('nan')
        nearest_lng=float('nan')

#Now compare the user's address to the shootings and see which is closest
from math import sin, cos, sqrt, atan2, radians

#Greatest distance between any two points in U.S. territory: 9,514 miles. 
#So, distances should be smaller than this and we are looking for the closest points
winning_distance=9514

# approximate radius of earth in km
R = 6373.0
lat1 = radians(abs(nearest_lat))
lng1 = radians(abs(nearest_lng))

for row in range(len(df_incident)):
    lat2 = radians(abs(df_incident.iloc[row]["Latitude"]))
    lng2 = radians(abs(df_incident.iloc[row]["Longitude"]))
    
    dlng = lng2 - lng1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlng / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    
    if distance<winning_distance:
        winning_distance=distance
        location_index=row

#The fatality/nonfatality/miss data is stored in a different API, so we will grab that info and cross reference by incident ID
#This will tell us if the shooting resulted in a fatality, nonfatality, or miss
#Victim API
url2 = "http://clt-charlotte.opendata.arcgis.com/datasets/2564657b1e9a4883ab388badadbeef6d_5.geojson"
response2 = requests.get(url2)
df_victim = pd.DataFrame(response2.json()['features'])
arr2 = []
for b in df_victim["properties"]:
    arr2.append(b)
df_victim = pd.DataFrame(arr2)
try:
    incident_num=df_incident.iloc[location_index]["INCIDENT_ID"]
    result=df_victim.loc[df_victim["INCIDENT_ID"]==incident_num,"INDIVIDUAL_INJURY_TYPE"].values
except:
    result="No shooting information found."

#Print the results, including the official recorded narrative
if result=="No shooting information found.":
    print("\n**********************************************************************\n")
    print("No closest shooting found. Check your address and try again.")
    print("\n**********************************************************************\n")
else:
    print("\n**********************************************************************\n")
    print("I have found the closest officer involved shooting to your search location.")
    print("\n**********************************************************************\n")
    print("Let me tell you about it:")
    print("In "+str(df_incident.iloc[location_index]["YR"])+ " there was a shooting at "+df_incident.iloc[location_index]["LOCATION"].title()+".")
    print("According to records, this is what happened:")
    #This prevents words from being chopped up
    text=textwrap.fill(df_incident.iloc[location_index]["NARRATIVE"])
    print(text+"\n")
    print("The shooting resulted in a "+str(result))