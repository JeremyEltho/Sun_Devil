import pandas as panda


ogFile= "Raw Data.csv" 
DataFrame = panda.read_csv(ogFile)
newFile = "filtered_file.csv" #name for the output csv


sorted_DataFrame = DataFrame.sort_values(by="Time (s)", ascending=True)  


var_z_score = 2.5  #variable to whatever z-score 2 is 95% 3 is 99.


Chosen_column= "Linear Acceleration x (m/s^2)" 


if Chosen_column in DataFrame.columns and panda.api.types.is_numeric_dtype(DataFrame[Chosen_column]):
    
    z_scores = (DataFrame[Chosen_column] - DataFrame[Chosen_column].mean()) / DataFrame[Chosen_column].std()

   
    filtered_DataFrame = DataFrame[z_scores.abs() < var_z_score]

    # savefile
    filtered_DataFrame.to_csv(newFile, index=False)



Chosen_column = "Linear Acceleration y (m/s^2)"  #wtvr column to edit

# doescolumn exist
if Chosen_column in DataFrame.columns and panda.api.types.is_numeric_dtype(DataFrame[Chosen_column]):
    # Calculate the z-scores for the specified column
    z_scores = (DataFrame[Chosen_column] - DataFrame[Chosen_column].mean()) / DataFrame[Chosen_column].std()

    # filter row using panda
    filtered_DataFrame = DataFrame[z_scores.abs() < var_z_score]

    # save to csv
    filtered_DataFrame.to_csv(newFile, index=False)



Chosen_column = "Linear Acceleration z (m/s^2)" 


if Chosen_column in DataFrame.columns and panda.api.types.is_numeric_dtype(DataFrame[Chosen_column]):
    
    z_scores = (DataFrame[Chosen_column] - DataFrame[Chosen_column].mean()) / DataFrame[Chosen_column].std()

    
    filtered_DataFrame = DataFrame[z_scores.abs() < var_z_score]

    
    filtered_DataFrame.to_csv(newFile, index=False)


print("CSV sorted and saved to:", newFile)
