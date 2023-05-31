# -*- coding: utf-8 -*-
"""
Created on Sun May 28 09:37:01 2023

@author: Jero
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.ticker import FixedLocator, FixedFormatter
import os

# Clean figures
plt.close('all')

# Read data from csv
data = pd.read_csv('UEFA_brackets_data.csv')

# Format season for data manipulation (removing the first year)
data['Season'] = data['Season'].apply(lambda x: int(x[0:4])+1)

# Get flag data for each country/season with error check
# Drop unnecessary columns
flags = data.drop(['Score','Team'],axis=1)
# Get flags grouped and return only the first flag to avoid duplicates
flags = flags.groupby(['Season','Country'])['Flag'].apply(lambda x: list(x)[0])

# Get score data for each country/season
score = data.drop(['Flag','Team'],axis=1).groupby(['Season','Country']).sum()

# Combine data in a single dataframe
data = score.merge(flags, how='outer', left_index=True, right_index=True)

# Rearrange data for plotting
data = data.reset_index().groupby(['Season',
                                   'Score',
                                   'Country'])['Flag'].apply(lambda x: list(x)[0])

######### Set up figure ########
# Set up sizes
plt.rcParams.update({'font.size': 16})
fig = plt.figure(figsize=(30,15))
fig.patch.set_facecolor('whitesmoke')
gspec = gridspec.GridSpec(1, 6, wspace=0)

# Subplot for data
trend =  plt.subplot(gspec[0, 0:5])

# Subplot for legend
legend =  plt.subplot(gspec[0, 5:])

# Get all the indexes for representation from dataframe
list_of_seasons = data.index.get_level_values('Season')            
list_of_scores = data.index.get_level_values('Score')

# Set up limits for data
trend.set_xlim([min(list_of_seasons)-1, max(list_of_seasons)+1])
trend.set_ylim([min(list_of_scores)-0.5, max(list_of_scores)+0.5])

# Define list for x-axis minor ticks 
xticks = list(range(min(list_of_seasons),max(list_of_seasons)+1,1))

# Define list for x-axis major ticks 
xticks_major = list(range(min(list_of_seasons),max(list_of_seasons)+1,5))

# Define list for y-axis major ticks 
yticks = list(range(min(list_of_scores),max(list_of_scores)+1,1))

# Define x-axis labels, converting years to seasons (YYYY-YY+1)
xlabels = [str(year-1)+"-"+str(year)[2:] for year in xticks_major] 

# Format axes ticks 
trend.xaxis.set_minor_locator(FixedLocator(xticks))
trend.xaxis.set_major_locator(FixedLocator(xticks_major))
trend.yaxis.set_major_locator(FixedLocator(yticks))

# Format x-axis labels and tick aspect 
trend.xaxis.set_major_formatter(FixedFormatter(xlabels))
trend.tick_params(axis="x", length=10)

# Format x-axis labels
trend.set_xticklabels(xlabels, rotation = 30)

# Format background color and swich grid on
trend.set_facecolor("gainsboro")
trend.grid()
trend.grid(which='minor')

# Format titles
trend.set_title("Which countries have dominated the European Cup and UEFA Champions League each season?")
trend.set_xlabel("Season")
trend.set_ylabel("Score")

# Define function to retrieve flags from folder
def getImage(flag):
    path = os.path.join(os.getcwd(),"flags",flag)
    return OffsetImage(plt.imread(path, format="png"), zoom=.8)

# Iterate over dataframe and plot each element
for season, season_df in data.groupby(level='Season'):
    for score, score_df in season_df.groupby(level='Score'):
        # Define an index to plot overlapping countries
        idx = 1
        for country, country_df in score_df.groupby(level='Country'):
            # Define figure markers (flags)
            marker = country_df.iloc[0] #A series with a single element
            
            # Define x position
            x = season
            
            # Define y position cosidering overlapping scores 
            offset = (idx-len(score_df))*0.2+(len(score_df)-1)*0.1
            y = score - offset
                                   
            # Define an object for custom markers
            ab = AnnotationBbox(getImage(marker), (x, y), frameon=False)
            trend.add_artist(ab)
            
            # Index for next country
            idx += 1
            
# Score explanation
explanation = """For each country, score is calculated by adding 
the individual score of the teams that reached 
any of the knockout rounds of the torunament: 
4 - winner, 3 - final, 2 - semi-finals, 1 - quarter-finals."""
trend.text(1960, 9, explanation, ha='left',va='center',wrap=True,
           fontsize=12,bbox=dict(boxstyle='square', fc='w', ec='k'))
            
######### Set up legend ########

# Arrange data from flag dataframe
countries = flags.reset_index().drop(['Season'],axis=1)

# Fix Germany data
countries.loc[countries['Country'] == 'West Germany','Country'] = 'Germany'
countries.loc[countries['Country'] == 'East Germany','Country'] = 'Germany'

# Fix Yugoslavia data
yugoslavia_str = 'Socialist Federal Republic of Yugoslavia'
countries.loc[countries['Country'] == yugoslavia_str,'Country'] = 'Yugoslavia'

# Fix CIS data for FC Dynamo Kyiv in 1992
CIS_str = 'Commonwealth of Independent States'
countries.loc[countries['Country'] == CIS_str,'Country'] = 'Ukraine'

# Get country-flags data
countries = countries.groupby('Country')['Flag'].apply(lambda x: list(set(x)))

# Set up limits for legend
yticks = list(range(len(countries)+1))
legend.set_ylim([min(yticks)-1, max(yticks)])
legend.set_xlim([0, 0.9])
legend.yaxis.tick_right()

# Hide axes, labels, marks
legend.axis('off')

# Iterate over the data to print flags and countries
row = 1
for country, country_flags in countries.items():   
    idx = 1    
    for flag in country_flags:
        # Define x position cosidering multiple flags
        offset = (idx-len(score_df))*0.1
        x = 0.1+offset
        
        # Define y position to list countries alphabetically
        y = len(countries)-row
        
        # Define an object for flags
        ab = AnnotationBbox(getImage(flag), (x, y), frameon=False)
        legend.add_artist(ab)        
                
        # Index for next flag
        idx += 1
        
    # Add the name of the country next to the flags
    legend.text(0.4, y, country, ha='left',va='center',wrap=True)
    
    # Index for next country
    row +=1 

plt.savefig(os.path.join(os.getcwd(),"figure")) 
plt.show()
plt.close(fig)