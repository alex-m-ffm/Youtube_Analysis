# YouTube Data Analysis for Dragonboat Paddling Channels

This repository contains Python scripts and Jupyter notebooks for analyzing YouTube data related to Dragonboat paddling channels. It includes functions to interact with the YouTube Data API to retrieve channel information, video data, activities, and analytics. The analysis aims to gain insights into channel performance, viewer engagement, and content trends.

You can read my analysis in my [blog post](https://alex.melemenidis.de/post/2024-03-19-why-i-am-not-viral/).

The code is strongly inspired by the great YouTube Tutorials on accessing the YouTube API by [Corey Schafer](https://www.youtube.com/@coreyms):\
Check them out here:
- [Getting Started - Creating an API Key and Querying the API](https://youtu.be/th5_9woFJmk)
- [Calculating the Duration of a Playlist](https://www.youtu.be/coZbOM6E47I)
- [Sort a Playlist by Most Popular Videos](https://www.youtu.be/1KO_HZtHOWI)
- [Using OAuth to Access User Accounts](https://youtu.be/vQQEaSnQ_bs)

To see what else is possible using look at the respective API references for the [YouTube Data API](https://developers.google.com/youtube/v3/docs) and the [YouTube Analytics API](https://developers.google.com/youtube/reporting).

And please check out and subscribe to my channels on YouTube, [the old, non-performing one](https://www.youtube.com/@AlexMelemenidis) and the hopefully more successful topic [dragonboat channel](https://www.youtube.com/@FFM-Mixup-DB)! 
▶️🙏

## Requirements

- Create a [Google Cloud](https://console.cloud.google.com/) project, enable the YouTube Data and Analytics APIs for it and create OAuth credentials. When setting up OAuth for the first time, in case you run into issues during the setup of the consent screen, play around with the app names. It seems some names like 'Youtube', 'Google' or similar are not allowed. (Even though the error message I got was that the 'Request was abusive.')
- Python 3.6 or higher
- Jupyter Notebook
- Required Python libraries (specified in `environment.yml`)

## Repository Structure

- `api_functions.py`: Python script containing functions to interact with the YouTube Data API.
- `youtube_analysis.ipynb`: Jupyter notebook for analyzing YouTube data regarding Dragonboat paddling channels.

## Usage

1. Clone the repository to your local machine:

`git clone <repository_url>`
`cd youtube-data-analysis`


2. Create a virtual environment in the current directory with the required dependencies using Conda:

`conda env create --prefix ./venv -f environment.yml`

Once the environment is created, activate it using:

`conda activate youtube-analysis`

3. Install the remaining required dependencies using pip:

`pip install -r requirements.txt`

4. In your Google Cloud project, download your credentials and store them as a file named  `client_secrets.json` in the root folder of this repository.

5. Run the `youtube_analysis.ipynb` notebook to perform data analysis and visualization.