FROM python:3.8
WORKDIR /traceability_module
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY ./traceability_module ./traceability_module
COPY ./traceability_module/records_table.csv ./traceability_module/records_table.csv
COPY ./traceability_module/032c4bb6-cf93-11ec-b196-2d3a3b4e88aa_ed25519 ./traceability_module/032c4bb6-cf93-11ec-b196-2d3a3b4e88aa_ed25519
COPY ./traceability_module/032c4bb6-cf93-11ec-b196-2d3a3b4e88aa_ed25519.pub ./traceability_module/032c4bb6-cf93-11ec-b196-2d3a3b4e88aa_ed25519.pub
COPY ./traceability_module/dc46341e-cf72-11ec-b196-2d3a3b4e88aa_ed25519 ./traceability_module/dc46341e-cf72-11ec-b196-2d3a3b4e88aa_ed25519
COPY ./traceability_module/dc46341e-cf72-11ec-b196-2d3a3b4e88aa_ed25519.pub ./traceability_module/dc46341e-cf72-11ec-b196-2d3a3b4e88aa_ed25519.pub
COPY ./traceability_module/1c0e8e40-ccc9-11ec-af24-8da70bfcced8_ed25519.pub ./traceability_module/1c0e8e40-ccc9-11ec-af24-8da70bfcced8_ed25519.pub
EXPOSE 5001
ENTRYPOINT ["python", "./traceability_module/main.py"]
CMD ["--smashhit_name='sender' --url_to_manager='http://localhost:5000'"]
