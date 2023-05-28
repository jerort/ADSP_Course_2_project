# -*- coding: utf-8 -*-
"""
Created on Thu May 25 13:43:00 2023

@author: Jero
"""

import csv
import pandas as pd
import os
import re

import traceback
import logging

import ssl
from urllib.request import urlopen
from urllib.request import urlretrieve
from bs4 import BeautifulSoup
from datetime import datetime

import team_func

# Ignore SSL certificate errors
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Read the main URL and generate a BeautifulSoup object
source = "https://en.wikipedia.org/wiki/List_of_European_Cup_and_UEFA_Champions_League_finals"
html = urlopen(source, context=ctx).read()
soup = BeautifulSoup(html, "html.parser")

# Retrieve certain tags for UEFA seasons
tags = soup.find_all(href=re.compile("\/wiki\/\d{4}\%"),
                     title=re.compile("\d{4,4}–\d{2}"))

seasons = {} #dictionary witohut duplicated URLs for each season
for tag in tags:    
    url =tag.get('href',None)
    season = tag.get('title',None)[0:7]
    seasons.update({season: url})
    
# Generate sorted dataframe from dictionary
seasons = pd.DataFrame([seasons]).T
seasons.columns = ['URL'] #rename column
seasons = seasons.sort_index()

# Remove upcoming finals from the lists
lastYear = datetime.now().year-1
seasons = seasons[seasons.index<str(lastYear)+"-"+str(lastYear+1)]

# Create folder to store flags
os.makedirs(os.path.join(os.getcwd(), "flags")) 

# Retrieve data for each season and append at the end of a file
idx = 1
for season, season_URL in seasons['URL'][:].items():
    print(f"Reading data for season {idx} ({season}) out of {len(seasons['URL'])}")
    try:
        ## Check if the file to save data exists and create it
        if not(os.path.isfile(os.path.join(os.getcwd(),"UEFA_brackets_data.csv"))):
            with open('UEFA_brackets_data.csv', 'w', newline='',
                      encoding="utf-8") as file:
                writer = csv.writer(file)    
                writer.writerow(["Season", "Team", "Score", "Country", "Flag"])
            file.close()           
                
        ## Check if the data for current season is already in the file
        if 'file_data' not in locals(): 
            with open('UEFA_brackets_data.csv', 'r', newline='',
                      encoding="utf-8") as file:
                file_data = pd.read_csv(file)
            file.close()            
        if list(file_data['Season']).count(season) == 16: 
            idx+=1
            continue            
        
        # Read the URL and generate a BeautifulSoup object
        html = urlopen("https://en.wikipedia.org"+season_URL, context=ctx).read()
        soup = BeautifulSoup(html, "html.parser")
        
        # Find the element containing the appropiate section 
        # Each section is given a score according to difficulty
        wikipedia_sections = [("Final", 3), #2T#This is always present
                              ("Semi-finals", 2), #4T #Missing in 92-93 and 91-93
                              ("Quarter-finals", 1)] #8T #Missing in 93-94, 92-93 and 91-93        
        
        #Other stages that might be incoporated before Quarter-finals
        # [("Second_group_stage", 0), #16T# replaces knockout stage for 1995-2003
        # ("Round_of_16", 0), #16T# 1st knockout stage from 2004...
        # ("Second_round", 0), #16T# 1st knockout stage for  1962...
        # ("First_round", 0), #16T# 1st knockout stage for  1955...                              
        # ("Preliminary_round", 0)] #16T# 1st knockout stage for  1956-1962...                              
        
        # Empty dictionaries to store data
        bracket = {}
        teams = {}
        
        # Find teams in each section
        for section, score in wikipedia_sections:
            
            # Try to find the name of the stage in the HTML body
            section_element = soup.find(id=section) 
            if not section_element: 
                if season in ["1991–92","1992–93","1993–94"]: #Not hyphens
                    section = "Group_stage" #League format with 8 teams equivalent ot quarters
                    score = 1
                    section_element = soup.find(id=section)
                else:    
                    continue            
            
            # Determing heading level for the section: h#
            heading_level = str(section_element.parent.name)
            # Determing preceding heading level for the section h#-1
            heading_level_0 = "h"+str(int(re.match("h(\d+)",
                                       heading_level).group(1))-1)  
            
            section_heding = section_element.find_previous(heading_level)
            
            # Since each team is attached the flag of its country, we can 
            # iterate over the section flags and get the data we need
            
            # Iterate through siblings until separator is found
            for sibling in section_heding.find_next_siblings():
                if (sibling.name == heading_level)or(sibling.name == heading_level_0):  
                    break
                for row in sibling.find_all("span", class_='flagicon'):
                    # Get the country name according to the flag
                    country = row.find_next("img").get('alt','Not defined')
                    flag_URL = "https:"+row.find_next("img").get('src',None)
                    flag_file = flag_URL.split("/")[-1]
                    
                    # Download flag image to folder
                    urlretrieve(flag_URL, os.path.join(os.getcwd(),
                                                       "flags",flag_file))
                    
                    # Get team and URL
                    (team_URL,team_name) = team_func.team_from_flag(row)    
                    
                    # Check just in case
                    if len(team_name) <= 1:
                        raise ValueError(f"""No team for flag {str(row.parent.parent)} 
                                    Check https://en.wikipedia.org{season_URL}""")                                          
                                        
                    # Create the team if not in the dictionary                
                    if team_URL not in teams: teams[team_URL] = (team_name,
                                                                 country,
                                                                 flag_file)  
                    
                    # Create/update the team score according to the round reached          
                    if bracket.get(team_URL, 0) < score:
                        bracket[team_URL] = score  
                                 
        # Determine the winner and add score
        summary = soup.find("table", class_="infobox vcalendar")
        finalists = summary.find_all("span", class_='flagicon')       
        
        # Two finalist should be found, being the first one the champions,
        # but it is checked anyway
        for finalist in finalists:
            if finalist.find_previous("th",scope="row",
                     class_="infobox-label").contents[0] == "Champions":
                team_URL = finalist.find_next("a").find_next("a").get('href',None)
                
                # Clean info between parentheses after the team URL
                result=re.match("(.*)\_\(.*\)", team_URL)
                if result: team_URL = result.group(1)
                
                # Standarise any dot in the the team URL: F.C. = FC
                team_URL = team_URL.replace('.', '')
                
                break
            else:
                team_URL = None
        
        # Add score to winner                
        bracket[team_URL] = bracket.get(team_URL, 0) + 1
        
        # Add score to "semi-finalists" 
        # (2nd team classified in each group of the group stage)
        if season in ["1991–92","1992–93"]: #Not hyphens
            for section in ["Group_A","Group_B"]:
                # Try to find the name of the stage in the HTML body
                section_element = soup.find(id=section)
                
                # Find the table with the classification
                table = section_element.find_next(class_="wikitable")
                                               
                # Find the second flag (team_URL) in the table
                flag = table.find_next("span", class_='flagicon')
                flag = flag.find_next("span", class_='flagicon')                
                
                
                # Get team and URL
                (team_URL,team_name) = team_func.team_from_flag(flag) 
                
                # Add score to "semi-finalists"               
                bracket[team_URL] = bracket.get(team_URL, 0) + 1
        
        # Fix Inter Milan issue (duplicated URL)
        bracket = team_func.remove_duplicate(bracket,
                                             "/wiki/Inter_Milan",
                                             "/wiki/FC_Internazionale_Milano")
        
        # Fix FC Barcelona issue (duplicated URL)
        bracket = team_func.remove_duplicate(bracket,
                                             "/wiki/FC_Barcelona",
                                             "/wiki/Barcelona_CF")       
        
        # Fix Malmö issue (duplicated URL)
        bracket = team_func.remove_duplicate(bracket,
                                             "/wiki/IFK_Malm%C3%B6_Fotboll",
                                             "/wiki/IFK_Malm%C3%B6")                           
        
        # Check the number of teams in each stage 
        if list(bracket.values()).count(4) != 1:
            raise ValueError(f"""There is not 1 winner team. 
                        Check https://en.wikipedia.org{season_URL}""") 
        if list(bracket.values()).count(3) != 1:
            raise ValueError(f"""There is not 1 team dropped in the Final. 
                        Check https://en.wikipedia.org{season_URL}""")
        if list(bracket.values()).count(2) != 2:
            raise ValueError(f"""There are not 4 teams dropped in Semi-finals. 
                        Check https://en.wikipedia.org{season_URL}""")
        if list(bracket.values()).count(1) != 4:
            raise ValueError(f"""There are not 4 teams dropped in Quarter-finals. 
                        Check https://en.wikipedia.org{season_URL}""")
        # if list(bracket.values()).count(0) != 8:
        #     raise ValueError(f"""There are not 8 teams dropped in the 1st round. 
        #                 Check https://en.wikipedia.org{season_URL}""")                
    
        # Save data to csv file    
        with open('UEFA_brackets_data.csv', 'a', newline='',
                  encoding="utf-8") as file:
            writer = csv.writer(file) 
            for key,val in bracket.items():
                writer.writerow([season, teams[key][0], val,
                                 teams[key][1], teams[key][2]])
        file.close()
        
    except Exception:
        logging.error(traceback.format_exc())
        print(f"Season {idx} ({season}) could not be processed")
    
    # End of proccessing    
    print("")
    idx+=1  
