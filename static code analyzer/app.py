import clang.cindex as clang

clang.Config.set_library_file(r"C:\Program Files\LLVM\bin\libclang.dll")

import streamlit as st
import tempfile
import json
from pathlib import Path
import os

from analyzer import Analyzer, ConstantCondition, EmptyBody, MissingBreak, UninitializedVar


st.set_page_config(page_title="Static C Code Analyzer", layout="wide")

st.title("🛡️ Static Code Analyzer for C")
st.markdown("Upload a `.c` file to analyze it for unsafe, unused, or problematic code patterns.")

uploaded_file = st.file_uploader("📁 Upload a C file", type=["c"])


if uploaded_file:
   
    file_bytes = uploaded_file.read()

    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".c") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    st.success(f"✅ Uploaded file saved temporarily as `{Path(tmp_path).name}`")

   
    try:
        code_contents = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        code_contents = file_bytes.decode("latin1")  # fallback for some encodings

    
    st.subheader("📄 Uploaded C Code with Line Numbers:")

    # Add line numbers
    numbered_code = "\n".join(
        f"{str(i+1).rjust(3)} | {line}" for i, line in enumerate(code_contents.splitlines())
    )

    
    st.code(numbered_code, language="c")


    try:
        index = clang.Index.create()
        tu = index.parse(tmp_path, args=["-std=c11"])

        analyzer = Analyzer()
        analyzer.register(ConstantCondition())

        analyzer.register(EmptyBody())
        
        analyzer.register(MissingBreak())
        
        
        analyzer.register(UninitializedVar())

        analyzer.analyze(tu)

        issues_json = [issue.as_dict() for issue in analyzer.issues]

        st.subheader("📝 Results (JSON format):")
        st.json(issues_json)
        

        st.subheader("📌 Summary of Issues by Rule:")
        rule_counts = {}
        for issue in issues_json:
            rule = issue["rule"]
            rule_counts[rule] = rule_counts.get(rule, 0) + 1


        if rule_counts:
            for rule, count in rule_counts.items():
                st.markdown(f"- **{rule}**: {count}")
        else:
            st.markdown("✅ No issues found.")

    except Exception as e:
        st.error(f"❌ Error during analysis: {e}")

    