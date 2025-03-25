import streamlit as st
import pathlib
import google.generativeai as genai
import pandas as pd
from io import BytesIO
from fpdf import FPDF
from main import (
    scrape_website,
    extract_body_content,
    clean_body_content,
    split_dom_content,
    detect_login_required,
    login_and_scrape,
)

def load_css(file_path):
    try:
        with open(file_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("CSS file not found.")

css_path = pathlib.Path("assets/style.css")
if css_path.exists():
    load_css(css_path)

def main():
    st.title("AI Scraper (Powered by Google Gemini)")
    st.markdown("Enter a website URL to scrape, clean the text content, and analyze it using AI.")

    if "site_requires_login" not in st.session_state:
        st.session_state.site_requires_login = False
    if "url_to_scrape" not in st.session_state:
        st.session_state.url_to_scrape = ""
    
    api_key = st.text_input("Enter your Google Gemini API key:", type="password")
    st.session_state.url_to_scrape = st.text_input("Enter the website URL to scrape:", value=st.session_state.url_to_scrape)
    parse_description = st.text_input("Describe the type of data to extract:")

    if st.button("Scrape"):
        if not api_key:
            st.error("Please enter a valid API key.")
            st.stop()
        if not st.session_state.url_to_scrape.strip():
            st.error("Please enter a valid URL.")
            st.stop()
        st.info("Scraping the website...")
        raw_html = scrape_website(st.session_state.url_to_scrape)
        if not raw_html:
            st.error("Failed to retrieve website content.")
            st.stop()
        if detect_login_required(raw_html):
            st.warning("Login required. Please provide credentials in the sidebar.")
            st.session_state.site_requires_login = True
        else:
            body_content = extract_body_content(raw_html)
            cleaned_content = clean_body_content(body_content)
            st.session_state.dom_content = cleaned_content
            st.success("Scraping complete!")
            st.text_area("Cleaned Results", cleaned_content, height=300)

    if st.session_state.site_requires_login:
        with st.sidebar:
            st.subheader("Website Login")
            if "login_username" not in st.session_state:
                st.session_state.login_username = ""
            if "login_password" not in st.session_state:
                st.session_state.login_password = ""
            st.session_state.login_username = st.text_input("Website Username", value=st.session_state.login_username)
            st.session_state.login_password = st.text_input("Website Password", type="password", value=st.session_state.login_password)
            if st.button("Login and Scrape"):
                if st.session_state.login_username and st.session_state.login_password:
                    st.info("Logging in and re-scraping...")
                    raw_html = login_and_scrape(st.session_state.url_to_scrape,
                                                st.session_state.login_username,
                                                st.session_state.login_password)
                    if not raw_html:
                        st.error("Login or scraping failed.")
                        st.stop()
                    body_content = extract_body_content(raw_html)
                    cleaned_content = clean_body_content(body_content)
                    st.session_state.dom_content = cleaned_content
                    st.session_state.site_requires_login = False
                    st.success("Scraping complete!")
                    st.text_area("Cleaned Results", cleaned_content, height=300)
                else:
                    st.error("Please enter both username and password.")

    if st.button("Extract Insights"):
        if not api_key:
            st.error("Please enter a valid API key.")
            st.stop()
        if "dom_content" not in st.session_state:
            st.error("Please scrape a website first.")
            st.stop()
        st.info("Extracting insights using Gemini AI...")
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-pro")
        except Exception as e:
            st.error(f"API Configuration Error: {e}")
            st.stop()
        dom_chunks = split_dom_content(st.session_state.dom_content)
        extracted_results = []
        for i, chunk in enumerate(dom_chunks, start=1):
            try:
                st.write(f"Processing chunk {i}...")
                prompt = (
                    "You are tasked with extracting specific information from the following text content: {dom_content}. "
                    "Please follow these instructions carefully: \n\n"
                    "1. **Extract Information:** Only extract the information that directly matches the provided description: {parse_description}. "
                    "2. **No Extra Content:** Do not include any additional text, comments, or explanations in your response. "
                    "3. **Empty Response:** If no information matches the description, return an empty string (''). "
                    "4. **Direct Data Only:** Your output should contain only the data that is explicitly requested, with no other text."
                )
                prompt = prompt.format(dom_content=chunk, parse_description=parse_description)
                response = model.generate_content(prompt)
                extracted_results.append(response.text if response.text else "")
            except Exception as e:
                st.error(f"Error processing chunk {i}: {str(e)}")
        extracted_text = "\n\n".join(extracted_results)
        st.session_state.extracted_text = extracted_text
        st.text_area("Extracted Data", extracted_text, height=300)

    if "extracted_text" in st.session_state:
        file_format = st.radio("Choose download format:", ["CSV (Tabular Format)", "Text", "PDF"])
        if file_format == "CSV (Tabular Format)":
            data = [line.split(",") for line in st.session_state.extracted_text.split("\n")]
            df = pd.DataFrame(data)
            csv_buffer = BytesIO()
            df.to_csv(csv_buffer, index=False, header=False)
            st.download_button("Download CSV", csv_buffer.getvalue(), "extracted_data.csv", "text/csv")
        elif file_format == "Text":
            text_buffer = BytesIO(st.session_state.extracted_text.encode("utf-8"))
            st.download_button("Download Text File", text_buffer.getvalue(), "extracted_data.txt", "text/plain")
        elif file_format == "PDF":
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_font("Arial", size=12)
            for line in st.session_state.extracted_text.split("\n"):
                safe_text = line.encode("latin-1", "ignore").decode("latin-1")
                pdf.multi_cell(0, 10, safe_text)
            pdf_output = pdf.output(dest='S').encode('latin-1')
            st.download_button("Download PDF", data=pdf_output, file_name="extracted_data.pdf", mime="application/pdf")

if __name__ == "__main__":
    main()
