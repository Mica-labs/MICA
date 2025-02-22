FROM hub2.20240220.xyz/python:3.9
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple fastapi gradio ruamel.yaml jsonpath langchain-community mysql-connector-python

COPY docker/run.sh /usr/bin/run.sh
COPY llmChatbot /llmChatbot

WORKDIR /llmChatbot
ENV PYTHONPATH=/
EXPOSE 5000
CMD ["bash", "/usr/bin/run.sh"]