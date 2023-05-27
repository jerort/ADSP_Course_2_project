# -*- coding: utf-8 -*-
"""
Created on Sat May 27 18:58:55 2023

@author: Jero

Returns the team name and URL, given a beatifulsoup object corresponding to 
the flag its country.
"""
import bs4
import re

def team_from_flag(flag_bs):
    # Try to get the team name and URL close to each flag
    flag_parent = flag_bs.parent.find_all("a")
    found = False
    for anchor in flag_parent:
        if type(anchor.contents[0])is bs4.element.NavigableString:
            # After finding the team there might by not useful info
            team_anchor = anchor 
            found = True
            break        
    if found == False:
        flag_parent = flag_bs.parent.parent.find_all("a")
        for anchor in flag_parent:
            if type(anchor.contents[0])is bs4.element.NavigableString:
                # After finding the team there might by not useful info
                team_anchor = anchor 
                found = True
                break
    
    if not found:
        return ("","")
    
    # If all is OK, then the URL shoud be found                
    team_URL = team_anchor.get('href',None)
  
    # Clean info between parentheses after the team URL
    result=re.match("(.*)\_\(.*\)", team_URL)
    if result: team_URL = result.group(1)
    
    # Standarise any dot in the the team URL: F.C. = FC
    team_URL = team_URL.replace('.', '') 
    
    # Also the name shoud be found          
    team_name = team_anchor.contents[0]
    
    # Clean info between parentheses after the team name
    result=re.match("(.*)\s+\(.*\)", team_name)
    if result: team_name = result.group(1)
    
    return (team_URL,team_name)

def remove_duplicate(bracket,URL1,URL2):
    if (URL1 in bracket) and (URL2 in bracket):
        if bracket.get(URL1) > bracket.get(URL2): 
            bracket.pop(URL2)
        else:
            bracket.pop(URL1)
    return bracket
    