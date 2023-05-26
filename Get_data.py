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
from bs4 import BeautifulSoup
from datetime import datetime


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

# Retrieve data for each season and append at the end of a file
idx = 1
for season, season_URL in seasons['URL'].items():
    print(f"Reading data for season {idx} ({season}) out of {len(seasons['URL'])}")
    try:
        ## Check if the file to save data exists and create it
        if not(os.path.isfile(os.path.join(os.getcwd(),"UEFA_brackets_data.csv"))):
            with open('UEFA_brackets_data.csv', 'w', newline='',
                      encoding="utf-8") as file:
                writer = csv.writer(file)    
                writer.writerow(["Season", "Team", "Country", "Score"])
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
        
        # Find the element containing the tournament bracket
        bracket_element = soup.find(id="Bracket")
        if not bracket_element: 
            raise ValueError(f"""Season {season} might not have a bracket table. 
                        Check https://en.wikipedia.org{season_URL}""")
        
        # Find the bracket table
        table = bracket_element.find_next("table")
        
        # Create a dictionaries to store the tournament bracket data
        bracket = {}
        finalists = {}
        teams = {}
        
        # Since each team is attached the flag of its country, we can iterate over
        # the table flags and get the data we need
        for row in table.find_all("span", class_='flagicon'):
            # Get the country name according to the flag
            country = row.find_next("img").get('alt','Not defined')
            team_anchor = row.find_next("a").find_next("a")
            team_URL = team_anchor.get('href',None)
            team_name = team_anchor.contents[0]
            teams[team_URL] = (team_name,country)
            if len(team_name) <= 3:               
                raise ValueError(f"""Team {team_name} might have a wrong name. 
                            Check https://en.wikipedia.org{season_URL}""")        
            
            # Clean info between parentheses after the team name
            result=re.match("(.*)\s+\(.*\)", team_name)
            if result: team_name = result.group(0)
            
            # After the team name, up to three cells display the goals scored
            # depending on the number of matches played   
            next_cell = team_anchor
            for scores in list(range(0,4,1)):
                next_cell = next_cell.find_next("td")
                if len(next_cell.contents) == 0: #No more info for the team
                    break
                
                # Store in case of finalist (only 1 match/score)  
                finalist_result = next_cell.contents[0] 
                
                # Check if the cell represents goals and penalties
                result=re.match("(\d+)\s+\((\d+)\)", finalist_result)
                # Penalties are added to goals to sort dictionary later
                if result: 
                    finalist_result = str(int(result.group(1))
                                          +int(result.group(2)))
                    
            if scores==1: # The team must be a finalist
                if team_name in finalists:
                    raise ValueError(f"""Team {team_name} might be a duplicated finalist. 
                                Check https://en.wikipedia.org{season_URL}""")
                finalists.update({team_URL: finalist_result})
                bracket[team_URL] = bracket.get(team_URL, 0) + 1 #Rounds counter
            elif scores==3: # The team has played 2 matches + global result
                bracket[team_URL] = bracket.get(team_URL, 0) + 1 #Rounds counter
            else:
                raise ValueError(f"""Team {team_name} might not have played any matches. 
                            Check https://en.wikipedia.org{season_URL}""")
        
        # As the number of teams in the bracket is not constant over seasons
        # we need to find the teams that played the preliminary round and 
        # decrease their score by 1. Then we can drop all the teams with 
        # 0 score 
        
        if len(bracket) > 16:
            # Find the element containing Preliminary Round rable
            preliminary = soup.find(id="Preliminary_round").find_next("table").find_next("table")              
            # Since each team that appears in the second table has played the
            # preliminary round, we can retrieve all their URLs and operate
            # with them
            preliminary_URLs = {}
            for anchor in preliminary.find_all("a"):                
                URL = anchor.get('href',None)
                preliminary_URLs.update({URL: None})
            
            # Decrease the score of teams in the premilimnary round by 1    
            for URL in preliminary_URLs.keys():  
                if URL in bracket.keys():
                    bracket[URL] -=1
            # Remove the teams that did not pass the premilimnary round            
            bracket = {key:val for key, val in bracket.items() if val != 0}
        
        # Data checks
        if len(bracket) != 16:
            raise ValueError(f"""There are not 16 teams in the tournament. 
                        Check https://en.wikipedia.org{season_URL}""")
        if len(finalists) != 2:
            raise ValueError(f"""There are not 2 finalists in the tournament.  
                        Check https://en.wikipedia.org{season_URL}""")                       
            
        # Determine the winner and add score
        finalists = sorted(finalists.items(), key=lambda item: item[1])
        winner = finalists[1][0]
        bracket[winner] = bracket.get(winner) + 1 
        
        # Count the number of tean in each round                      
        if list(bracket.values()).count(1) != 8:
            raise ValueError(f"""There are not 8 teams dropped in the 1st round. 
                        Check https://en.wikipedia.org{season_URL}""")
        if list(bracket.values()).count(2) != 4:
            raise ValueError(f"""There are not 4 teams dropped in Quarter-finals. 
                        Check https://en.wikipedia.org{season_URL}""")        
        if list(bracket.values()).count(3) != 2:
            raise ValueError(f"""There are not 4 teams dropped in Semi-finals. 
                        Check https://en.wikipedia.org{season_URL}""")
        if list(bracket.values()).count(4) != 1:
            raise ValueError(f"""There is not 1 team dropped in the Final. 
                        Check https://en.wikipedia.org{season_URL}""")         
        if list(bracket.values()).count(5) != 1:
            raise ValueError(f"""There is not 1 winner team. 
                        Check https://en.wikipedia.org{season_URL}""") 
    
        # Save data to csv file    
        with open('UEFA_brackets_data.csv', 'a', newline='',
                  encoding="utf-8") as file:
            writer = csv.writer(file) 
            for key,val in bracket.items():
                writer.writerow([season, teams[key][0],teams[key][1], val])
        file.close()
        
    except Exception:
        logging.error(traceback.format_exc())
        print(f"Season {idx} ({season}) could not be processed")
    
    # End of proccessing    
    print("")
    idx+=1
        
