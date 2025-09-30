import streamlit as st 
from uuid import uuid1

def initialize_session_state():
    if 'session-state' not in st.session_state:
        st.session_state['session-id'] = str(uuid1())
        
    if 'docs' not in st.session_state:
        st.session_state['docs'] = None
        
    if 'processed' not in st.session_state:
        st.session_state['processed'] = []
        
    if 'db' not in st.session_state:
        st.session_state['db'] = None