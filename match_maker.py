import json
import lorem
import base64
import datetime
import requests
import bs4 as bs
import pandas as pd
from PIL import Image
import streamlit as st
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS

st.set_page_config(layout="wide", initial_sidebar_state="expanded", page_title="Match Maker")

keywords = [
    'Data', 'Data Scientist', 'Data Engineer', 'Data Analyst', 'Data Architect', 'Data Science',
    'Data Analytics', 'Data Visualization', 'Data Mining', 'Data Warehouse', 'Data Lake', 'Data Mart',
    'Data Quality', 'Data Governance', 'Data Management', 'Data Integration', 'Data Architecture', 'Data Engineering'
]

your_ideal_stack_text = """Statistical analysis and computing, Machine Learning, Deep Learning,
                            Processing large data sets, 
                            Data Visualization, Data Wrangling,Mathematics, Programming, Statistics, Big Data,
                            Data Mining, Data Science, Data Engineering, Data Architecture, Data Analytics,
                            Data Management,Data Governance, Data Quality, Data Integration, Data Warehousing,
                            Data Modeling,Fundamentals of Data Science Statistics Programming knowledge 
                            Data Manipulation and Analysis Data Visualization Machine Learning Deep Learning Big Data
                            software Engineering Model Deployment Communication Skills
                            Storytelling Skills Structured Thinking
                            Curiosity Creativity
                            Problem Solving Critical Thinking
                        """ + " ".join(lorem.paragraph().split(" "))

wordcloud = WordCloud(stopwords=STOPWORDS, max_font_size=50, max_words=15, background_color="#F1F1F1", colormap='Set2',
                      collocations=False, random_state=1).generate(your_ideal_stack_text)
wordcloud.to_file("png/lorem_stack_wordcloud.png")

# use bcjobs.ca api to query jobs data. Response contains only the latest 10 job ads.
url = f'https://www.bcjobs.ca/api/v1.1/public/jobs?'


def main():
    st.title("Match Maker")
    st.subheader("Attempts to match skills to relevant job postings...")
    st.markdown(f"""This app is a simple job matching tool that uses the bcjobs.ca API to query the latest job ads. 
    The app uses the job description to generate a word cloud of the most used (default 15 ) non stop words and then 
    tries to match the job ads that have a similar word cloud from the user's skill sets. 
    Copy your stack in one of the first text area and let the app build your word cloud, then see if there is a visual
     match. Will come up with a similarity score later... 
    Maybe a Hu Moments based similarity score? 
    """)

    def make_api_call(url):
        """
        This function takes in a url and returns a json object
        """
        response = requests.get(url)
        if response.ok:
            request_info_ = json.loads(str(response.content, 'utf-8'))  # convert the json response to an object
        else:
            if response.status_code == 400:
                error = json.loads(str(response.content, 'utf-8'))
                st.error(error)
            else:
                st.error('Error {} - {}'.format(response.status_code, response.reason))

        return request_info_

    def make_clickable(url_):
        return '<a href="{}" target="_blank">Link to job ad</a>'.format(url)

    @st.cache
    def get_job_description(request_info_):
        """
        This function takes in a dataframe and adds a string of the job description column.
        Shaky stuff since the html parser is not very robust
        """
        df_ = pd.DataFrame()
        for i_ in range(len(request_info_['data'])):
            dict_ = {k: request_info_['data'][i_].get(k) for k in
                     ['title', 'locations', 'publishDate', 'employer', 'url']}
            dict_.update({'locations': '{}, {}'.format(request_info_['data'][0].get('locations')[0].get('description'),
                                                       request_info_['data'][0].get('locations')[-1].get('type')),
                          'employer': request_info_['data'][i_].get('employer').get('name')})
            df_ = df_.append(dict_, ignore_index=True)

        for i_, url_ in enumerate(df_.url):
            job_url = f'https://www.bcjobs.ca{url_}'
            r = requests.get(job_url)
            soup = bs.BeautifulSoup(r.text, 'lxml')
            meta_data = soup.find('div', class_="clearfix u_mt-md")
            try:
                position_type, posted = meta_data.text.split('Details')[1].strip().split(
                    '\n\n\n')  # get the position type and posted date
                df_.loc[i_, 'position_type'] = position_type.strip()
                df_.loc[i_, 'posted'] = posted.strip()
            except:
                pass

            job_desc = soup.find('div', class_='clearfix u_text--90 u_mb-base u_overflow-hidden').text
            df_.loc[i_, 'job_description'] = job_desc
            df_.loc[i_, 'job_url'] = job_url

        df_.drop(columns=['url'], inplace=True)

        return df_

    request_info = make_api_call(url)
    df = get_job_description(request_info)
    tot_number_of_jobs = len(df)

    filters = st.multiselect("Select phrases", keywords, default=None)

    filters = "|".join([x.replace(" ", "") for x in filters if x])

    add_your_own_keywords = st.text_input("Add your own key word(s). eg., Data Developer", value="")
    if add_your_own_keywords:
        filters += "|" + add_your_own_keywords.replace(" ", "")

    df = df[df['job_description'].apply(lambda x: x.replace(" ", "")).str.contains(filters, case=False,
                                                                                   regex=True)].reset_index(drop=True)

    if len(df) == 0:
        st.info(f"""Ⓘ Sorry, no job found based on the filters used at this time.
                    Try using different keywords or check back later.
                 """)
        st.stop()
    else:
        st.info(f"""Ⓘ {len(df)} job(s) found based on the filters used.
                 """)

    def xy(df_):
        return [f'[{title}]({job_url})' for title, job_url in zip(df_.title, df_.job_url)]

    df.title = xy(df[['title', 'job_url']])

    job_xpdr = st.expander('Latest Jobs', expanded=True)

    cols = job_xpdr.columns([4, 2, 2, 2, 2, 2])  # (len(df.columns)+4)

    dff = df.drop(columns=['job_description', 'job_url'])
    # first write the headers
    for i, h in enumerate(dff.columns):
        cols[i].markdown(f'<span style="font-size:24px">{h}</span>', unsafe_allow_html=True)

    for i, cl in enumerate(dff.columns):

        for _, line in enumerate(dff[cl].values):
            cols[i].markdown(f'<span style="font-size:16px">{line}</span>', unsafe_allow_html=True)

    st.markdown(
        f'<h6 style="color:white;font-size:24px;border-radius:0%;background-color:#754DF3;">Job Summaries & Wordclouds<br></h6></br>',
        unsafe_allow_html=True)
    word_max = st.slider('Wordcloud Max', min_value=10, max_value=45, value=15, step=5)

    st.write(f"""Copy text containing your skills, experience, etc. in the text box below. 
                                            By default, a random word list is generated using some common data science 
                                            skills plus some noise (see lorem). 
                                             The app will generate a wordcloud of the most used words in your text. 
                                             The wordcloud will be used to match your skills with the job ads.""")

    your_true_stack_text_ = st.text_input(label="", value="",
                                          key=f"your_stack_text_")

    if your_true_stack_text_ != "":
        your_true_stack_wordcloud = WordCloud(stopwords=STOPWORDS, max_font_size=50, max_words=word_max,
                                              background_color="#F1F1F1", colormap='Set2', collocations=False).generate(
            your_true_stack_text_)
        your_true_stack_wordcloud.to_file("png/your_stack_wordcloud.png")

    for i in range(len(df)):
        cols = st.columns([1.5, 1.25, 1.25])
        job_title = df['title'].values[i]

        text_ = cols[0].text_area(label="Job Summary", value=df['job_description'].values[i], height=250,
                                  key=f"input_area_key_{i}")

        if text_:
            wordcloud = WordCloud(stopwords=STOPWORDS, max_font_size=50, max_words=word_max, background_color="#F1F1F1",
                                  colormap='Set2', collocations=False, random_state=1).generate(text_)
            wordcloud.to_file("png/job_cloud.png")
            cols[1].markdown(
                f'<span style="font-size:16px;border-radius:0%;"> {"Required Skills (Go to the job ad 👉 "} {job_title})</span>',
                unsafe_allow_html=True)
            cols[1].markdown(
                f'<img src="data:image/png;base64,{base64.b64encode(open("png/job_cloud.png", "rb").read()).decode()}" alt="word cloud" width="600" height="250">',
                unsafe_allow_html=True)

            cols[2].markdown(f'<span style="font-size:16px;border-radius:0%;">Your Skills </span>',
                             unsafe_allow_html=True)

            if your_true_stack_text_ != "":
                cols[2].markdown(
                    f'<img src="data:image/png;base64,{base64.b64encode(open("png/your_stack_wordcloud.png", "rb").read()).decode()}" alt="word cloud" width="600" height="250">',
                    unsafe_allow_html=True)
            else:
                cols[2].markdown(
                    f'<img src="data:image/png;base64,{base64.b64encode(open("png/lorem_stack_wordcloud.png", "rb").read()).decode()}" alt="word cloud" width="600" height="250">',
                    unsafe_allow_html=True)

            st.markdown(f'<h6 style="background-color:#754DF3;"></h6>', unsafe_allow_html=True)

    if st.checkbox("show raw data"):
        df_show = df.copy()
        df_show = df_show.to_html(escape=False)
        st.write(df_show, unsafe_allow_html=True)

    # Note

    st.info(f"""Ⓘ This app is still in development. The api url used is https://www.bcjobs.ca/api/v1.1/public/jobs?. 
    It does not require any authentication but as of {datetime.datetime.today().date()} it limits the response to only 
    {tot_number_of_jobs} jobs per query.
    """)


if __name__ == "__main__":
    main()
