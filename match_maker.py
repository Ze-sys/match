import json
import lorem
import base64
import datetime
import requests
import bs4 as bs
import pandas as pd
import streamlit as st
import plotly.express as px
from wordcloud import WordCloud, STOPWORDS
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode, JsCode

st.set_page_config(layout="wide", initial_sidebar_state="collapsed", page_title="Match Maker")

keywords = [
    'Data', 'Data Scientist', 'Data Engineer', 'Data Analyst', 'Data Architect', 'Data Science',
    'Data Analytics', 'Data Visualization', 'Data Mining', 'Data Warehouse', 'Data Lake', 'Data Mart',
    'Data Quality', 'Data Governance', 'Data Management', 'Data Integration', 'Data Architecture', 'Data Engineering'
]

your_ideal_stack_text =  [lorem.paragraph() for _ in range(2)]

wordcloud = WordCloud(stopwords=STOPWORDS, max_font_size=50, max_words=15, background_color="#F1F1F1", colormap='Set2',
                      collocations=False, random_state=1).generate(your_ideal_stack_text[0])
wordcloud.to_file("png/lorem_stack_wordcloud.png")

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
            salary_amount= meta_data.text.split('Salary')[1].strip().split('\n')[0].strip()
        except IndexError:
            salary_amount = 'N/A'
            pass

        try:
            location= meta_data.text.split('Location')[1].strip().split('\n')[0].strip()
        except IndexError:
            location = 'N/A'
            pass

        try:
            position_type, posted = meta_data.text.split('Details')[1].strip().split(
                '\n\n\n')  # get the position type and posted date
        except ValueError:
            position_type, posted = 'N/A', 'N/A'
            pass

        try:
            category = soup.find_all('a',class_="rf_tag u_mb-xxs u_mr-xxs")[-1].text.strip('\n')
        except IndexError:
            category = 'N/A'
            pass


        df_.loc[i_, 'position'] = position_type
        df_.loc[i_, 'location'] = location
        df_.loc[i_, 'posted'] = posted.strip()
        job_desc = soup.find('div', class_='clearfix u_text--90 u_mb-base u_overflow-hidden').text
        df_.loc[i_, 'job_description'] = job_desc
        df_.loc[i_, 'job_url'] = job_url
        df_.loc[i_, 'category'] = category
        df_.loc[i_, 'salary'] = salary_amount

        

    df_.drop(columns=['url'], inplace=True)

    return df_



def main():
    st.title("Match Maker")
    st.subheader("Attempts to match skills to relevant job postings...")
    st.markdown(f"""This app is a simple job matching tool that uses the bcjobs.ca API to query the available job ads. The total number of jobs queried (number of jobs per query + number of pages) can be set from the sidebar on the left. 
    The app uses the job description from user selected rows in the table below to generate a word cloud of the most used (default 15) words. And then, it 
    tries to evaluate the match the user's skills with those in the job ad. Copy your stack/skills list in the text box  and let the app build your word cloud. 
    By default, the first 3 jobs are are used to build word clouds. This  can be changed by adding/removing  jobs from the table.
    See if there is a visual match. Will come up with a similarity score later... 
    Maybe a Hu Moments based similarity  between the two word cloud images ? 
    """)
    

    jobs_per_query=st.sidebar.selectbox('Select number of jobs per query (default is 10. Bigger numbers take longer to get response. Smaller numbers result in more round trips to the aip server. Make your call!', 
                         [10, 20, 30, 40, 50, 60, 70, 80, 90, 100], index=0)
    
    url = f'https://www.bcjobs.ca/api/v1.1/public/jobs?page=1&pageSize={jobs_per_query}'

    max_number_of_pages_to_query = st.sidebar.slider('Max number of pages to query (default is 5)', min_value=1, max_value=100, value=5, step=1)



    st.sidebar.markdown("""---""")
    st.sidebar.markdown("""Table layout Options, credit: [Pablo Fonseca](https://github.com/PablocFonseca/streamlit-aggrid)""") 
    # AgGrid settings

    grid_height = st.sidebar.number_input("Grid height", min_value=200, max_value=800, value=300)
    return_mode = st.sidebar.selectbox("Return Mode", list(DataReturnMode.__members__), index=1)
    return_mode_value = DataReturnMode.__members__[return_mode]
    update_mode = st.sidebar.selectbox("Update Mode", list(GridUpdateMode.__members__), index=len(GridUpdateMode.__members__)-1)
    update_mode_value = GridUpdateMode.__members__[update_mode]
    #enterprise modules
    enable_enterprise_modules = st.sidebar.checkbox("Enable Enterprise Modules")
    if enable_enterprise_modules:
        enable_sidebar =st.sidebar.checkbox("Enable grid sidebar", value=False)
    else:
        enable_sidebar = False

    #features
    fit_columns_on_grid_load = st.sidebar.checkbox("Fit Grid Columns on Load")

    enable_selection=st.sidebar.checkbox("Enable row selection", value=True)
    if enable_selection:
        st.sidebar.subheader("Selection options")
        selection_mode = st.sidebar.radio("Selection Mode", ['single','multiple'], index=1)

        use_checkbox = st.sidebar.checkbox("Use check box for selection", value=True)
        if use_checkbox:
            groupSelectsChildren = st.sidebar.checkbox("Group checkbox select children", value=True)
            groupSelectsFiltered = st.sidebar.checkbox("Group checkbox includes filtered", value=True)

        if ((selection_mode == 'multiple') & (not use_checkbox)):
            rowMultiSelectWithClick = st.sidebar.checkbox("Multiselect with click (instead of holding CTRL)", value=False)
            if not rowMultiSelectWithClick:
                suppressRowDeselection = st.sidebar.checkbox("Suppress deselection (while holding CTRL)", value=False)
            else:
                suppressRowDeselection=False

    enable_pagination = st.sidebar.checkbox("Enable pagination", value=False)
    if enable_pagination:
        st.sidebar.subheader("Pagination options")
        paginationAutoSize = st.sidebar.checkbox("Auto pagination size", value=True)
        if not paginationAutoSize:
            paginationPageSize = st.sidebar.number_input("Page size", value=5, min_value=0, max_value=100)
        st.sidebar.text("___")

    #------------end AgGrid settings------------------------------



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


    request_info = make_api_call(url)
    df = get_job_description(request_info)

    # st.write(request_info['paging'])
    latest_iteration = st.empty()
    prog_bar = st.progress(0)

    while request_info['paging'].get('page') < max_number_of_pages_to_query:  # get the next 10 pages of job ads
        request_info = make_api_call(request_info['paging'].get('next'))
        latest_iteration.text(f'Loading page {request_info["paging"].get("page")} of {max_number_of_pages_to_query}...')
        prog_bar.progress(0 + request_info['paging'].get('page') / max_number_of_pages_to_query)
            
        df = df.append(get_job_description(request_info), ignore_index=True)
        df = pd.concat([df,get_job_description(request_info)], ignore_index=True)
        if request_info['paging'].get('next') is None:
            break


    tot_jobs_queried = len(df)

    filters = st.multiselect("Select phrases", keywords, default=None)

    filters = "|".join([x.replace(" ", "") for x in filters if x]) + "|"

    add_your_own_keywords = st.text_input("Add your own key word(s) separated by a comma. eg., Data Developer, Database Administrator", value="")
    if add_your_own_keywords:
        for x in add_your_own_keywords.split(","):
            if x:
                filters +=   x.replace(" ", "") + "|" 

    filters = filters.strip("|")  # remove the last pipe

    df = df[df['job_description'].apply(lambda x: x.replace(" ", "")).str.contains(filters, case=False,
                                                                                   regex=True)].reset_index(drop=True)

    if len(df) == 0:
        st.info(f"""Ⓘ Sorry, no job found based on the filters used at this time.
                    Try using different keywords or check back later.
                 """)
        st.stop()
    else:
        st.info(f"""Ⓘ As of {datetime.datetime.today().date()}, there are
    {request_info['paging'].get('total')} jobs in the database. A total {tot_jobs_queried } jobs queried. {len(df)} job(s) found based on the filters used.
                 """)

    def xy(df_):
        return [f'[{title}]({job_url})' for title, job_url in zip(df_.title, df_.job_url)]


    job_xpdr = st.expander('Jobs', expanded=True)

    cols = job_xpdr.columns([4, 2, 2, 2, 2, 2, 2]) 

   
    with job_xpdr:

        gb_models = GridOptionsBuilder.from_dataframe(df)
        gb_models.configure_grid_options(domLayout='normal')
        gb_models.configure_column("title", headerCheckboxSelection = True)
        gb_models.configure_selection('multiple', use_checkbox=True, pre_selected_rows=[0, 1, 2]) # show the first 3 rows as selected for wordcloud
        gb_models.configure_pagination(paginationAutoPageSize=True)


        gridOptions_models = gb_models.build()
        grid_response_models = AgGrid(
            df, 
            gridOptions=gridOptions_models,
            height=grid_height, 
            width='100%',
            data_return_mode=return_mode_value, 
            update_mode=update_mode_value,
            fit_columns_on_grid_load=fit_columns_on_grid_load,
            allow_unsafe_jscode=True, 
            enable_enterprise_modules=enable_enterprise_modules
        )

        selected_rows_ = grid_response_models['selected_rows']

        df_show = pd.DataFrame(selected_rows_)

    barcharts_xpdr = st.expander('Jobs by category', expanded=False)

    with barcharts_xpdr:

        category_counts = df.groupby('category').count().sort_values(by='title', ascending=False)
        AgGrid(category_counts.T.head(1),fit_columns_on_grid_load=True,height=60)
        
        fig = px.bar(df, x='category', color='category', color_discrete_sequence=px.colors.qualitative.Dark24, hover_data=['title', 'salary','posted'])
   
        fig.update_layout(
            xaxis = dict(
                    showgrid = True,
                    showticklabels = False,
                ),
            title = '',
            xaxis_title = 'category',
            yaxis_title = 'number of jobs',
            font=dict(
                family="Times New Roman",
                size=18,
                color="#7f7f7f"
            ),
            legend_title_text='category',
            legend=dict(
                yanchor="top",
                y=2,
                xanchor="left",
                x=0.01,
                orientation="h"
             ),
        )
          
        st.plotly_chart(fig, use_container_width=True)
      


    st.markdown(
        f'<h6 style="color:white;font-size:24px;border-radius:0%;background-color:#754DF3;">Job Summaries & Wordclouds<br></h6></br>',
        unsafe_allow_html=True)
    word_max = st.slider('Wordcloud Max', min_value=10, max_value=45, value=15, step=5)

    st.write(f"""Copy text containing your skills, experience, etc. in the text box below. 
                                             The app will generate a word  cloud of the most common words in your text. 
                                             The word cloud will be used to match your skills with the job ads.""")

    your_true_stack_text_ = st.text_input(label="Copy your text 👇", value="",
                                          key=f"your_stack_text_")

    if your_true_stack_text_ != "":
        your_true_stack_wordcloud = WordCloud(stopwords=STOPWORDS, max_font_size=50, max_words=word_max,
                                              background_color="#F1F1F1", colormap='Set2', collocations=False).generate(
            your_true_stack_text_)
        your_true_stack_wordcloud.to_file("png/your_stack_wordcloud.png")

    for i in range(min(5,len(df_show))):
        job_link_container = st.container()
        def job_link(x):
            return  f"""[![Go to job](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)]({x})""",

        cols = st.columns([1.25, 1.25, 1.25])
        job_title = xy(df[['title', 'job_url']].iloc[i:i + 1])[0]

        text_ = cols[0].text_area(label="Job Summary", value=df_show['job_description'].values[i], height=250,
                                  key=f"input_area_key_{i}")

        if text_:
            wordcloud = WordCloud(stopwords=STOPWORDS, max_font_size=50, max_words=word_max, background_color="#F1F1F1",
                                  colormap='Set2', collocations=False, random_state=1).generate(text_)
            wordcloud.to_file("png/job_cloud.png")

            cols[1].markdown(
                f'<span style="font-size:16px;border-radius:0%;"> {"Required Skills"} ({job_title})</span>',
                unsafe_allow_html=True)
            cols[1].markdown(
                f'<img src="data:image/png;base64,{base64.b64encode(open("png/job_cloud.png", "rb").read()).decode()}" alt="word cloud" width="500" height="250">',
                unsafe_allow_html=True)

            cols[2].markdown(f'<span style="font-size:16px;border-radius:0%;">Your Skills (copy some text in the box above) </span>',
                             unsafe_allow_html=True)

            if your_true_stack_text_ != "":
                cols[2].markdown(
                    f'<img src="data:image/png;base64,{base64.b64encode(open("png/your_stack_wordcloud.png", "rb").read()).decode()}" alt="word cloud" width="525" height="250">',
                    unsafe_allow_html=True)
            else:
                cols[2].markdown(
                    f'<img src="data:image/png;base64,{base64.b64encode(open("png/lorem_stack_wordcloud.png", "rb").read()).decode()}" alt="word cloud" width="525" height="250">',
                    unsafe_allow_html=True)

            st.markdown(f'<h6 style="background-color:#754DF3;"></h6>', unsafe_allow_html=True)


    st.info(f"""Ⓘ This app is still under development. 
            """)



if __name__ == "__main__":
    main()
