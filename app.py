from pathlib import Path
from tkinter import filedialog
import tkinter as tk
import os
import calendar
from datetime import datetime
from typing import Callable, Iterable, List, Optional

import streamlit as st
from streamlit_option_menu import option_menu

from fdk.storage.gateway import TModel, fdk_gateway
from fdk.storage.json.gateway import fdk_import_gateway

db = fdk_gateway()


# -------------- SETTINGS --------------
incomes = ['Salary', 'Blog', 'Other Income']
expenses = ['Rent', 'Utilities', 'Groceries', 'Car', 'Other Expenses', 'Saving']
page_title = 'SBB-FDK Übersicht'
page_icon = ':card_file_box:'  # emojis: https://www.webfx.com/tools/emoji-cheat-sheet/
layout = 'centered'
# --------------------------------------

st.set_page_config(page_title=page_title, page_icon=page_icon, layout=layout)
st.title(page_title + ' ' + page_icon)


def _select_folder() -> Path:
    root = tk.Tk()
    root.withdraw()
    # Make folder picker dialog appear on top of other windows
    root.wm_attributes('-topmost', 1)
    return Path(filedialog.askdirectory(master=root)).absolute()


def _text(models: List[TModel], text: str, count: Optional[int] = None):
    count = len(models) if count is None else count
    model_count = str(len(models))
    count_with_zeros = f'{count}'.zfill(len(model_count))
    return f'{count_with_zeros}/{model_count}: {text}'


def _grouped_models(models: Iterable[TModel], group_size: int) -> List[Iterable[TModel]]:
    model_groups = []
    group = []
    for model in models:
        group.append(model)
        if len(group) == group_size:
            model_groups.append(group)
            group = []
    if len(group) > 0:
        model_groups.append(group)
    return model_groups


def import_models(models: List[TModel], model_name: str, callback: Callable[[Iterable[TModel]], None], group_size: int = 25):
    pregress = f'Import "{model_name}" in progress. Please wait.'
    progress_bar = st.progress(0, text=pregress)
    model_count = len(models)
    index = 0
    for group in _grouped_models(models, group_size):
        callback(group)
        index += 1
        count = index * group_size
        percent = min(count/model_count, 1)
        progress_bar.progress(percent, text=_text(models, pregress, count))
    progress_bar.progress(1.0, text=_text(models, pregress))


def delete_models(model_name: str, callback: Callable[[], None]):
    pregress = f'Delete "{model_name}" in progress. Please wait.'
    st.progress(0, text=pregress)
    callback()


# --- HIDE STREAMLIT STYLE ---
# hide_ st_style = '''
#             <style>
#             #MainMenu {visibility: hidden;}
#             footer {visibility: hidden;}
#             header {visibility: hidden;}
#             </style>
#             '''
# st.markdown(hide_st_style, unsafe_allow_html=True)


# --- NAVIGATION MENU ---
selected = option_menu(
    menu_title=None,
    options=['Import', 'Visualization'],
    icons=['pencil-fill', 'bar-chart-fill'],  # https://icons.getbootstrap.com/
    orientation='horizontal',
)

if selected == 'Import':
    st.header(f'FDK Import')
    col1, col2 = st.columns([1, 2])
    col1.text('Please select a folder:')
    clicked = col2.button('FDK-Path')
    if clicked:
        path = _select_folder()
        st.text_input('Selected:', path if path.exists() else 'Path does not exists')
        if path.exists():
            file_gw = fdk_import_gateway(path)
            '---'
            delete_models('FDK Property', db.delete_properties)
            delete_models('FDK Property Set', db.delete_psets)
            delete_models('FDK Object', db.delete_objects)
            '---'
            import_models(file_gw.properties(), 'FDK Property', db.save_properties)
            import_models(file_gw.psets(), 'FDK Property Set', db.save_psets)
            import_models(file_gw.objects(), 'FDK Object', db.save_objects)
            st.success('Data saved!')
        clicked = not clicked


if selected == 'Visualization':
    st.header('Visualization')
    with st.form('saved_periods'):
        prop_name = st.selectbox('Select Property Names:', db.property_names())
        submitted = st.form_submit_button('Property Overview')
        if submitted:
            # Get data from database
            properties = db.properties_by_name(prop_name)
            st.write(properties)
            # st.write(sorted(properties, key=lambda prop: prop.fdk_id))
            # comment = period_data.get('comment')
            # expenses = period_data.get('expenses')
            # incomes = period_data.get('incomes')

            # # Create metrics
            # total_income = sum(incomes.values())
            # total_expense = sum(expenses.values())
            # remaining_budget = total_income - total_expense
            # col1, col2, col3 = st.columns(3)
            # col1.metric('Total Income', f'{total_income} {currency}')
            # col2.metric('Total Expense', f'{total_expense} {currency}')
            # col3.metric('Remaining Budget', f'{remaining_budget} {currency}')
            # st.text(f'Comment: {comment}')

            # # Create sankey chart
            # label = list(incomes.keys()) + ['Total Income'] + list(expenses.keys())
            # source = list(range(len(incomes))) + [len(incomes)] * len(expenses)
            # target = [len(incomes)] * len(incomes) + [label.index(expense)
            #                                           for expense in expenses.keys()]
            # value = list(incomes.values()) + list(expenses.values())

            # # Data to dict, dict to sankey
            # link = dict(source=source, target=target, value=value)
            # node = dict(label=label, pad=20, thickness=30, color='#E694FF')
            # data = go.Sankey(link=link, node=node)

            # # Plot it!
            # fig = go.Figure(data)
            # fig.update_layout(margin=dict(l=0, r=0, t=5, b=5))
            # st.plotly_chart(fig, use_container_width=True)
