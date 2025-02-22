import gradio as gr
import asyncio


# 定义异步函数，每秒触发一次submit()
async def auto_submit(state, last_input_time):
    while True:
        await asyncio.sleep(1)  # 每秒执行一次
        state += "Bot: Checking for inactivity...\n"  # 模拟机器人输出
        last_input_time = asyncio.get_event_loop().time()

        # 返回更新后的对话框内容
        yield gr.update(value=state)
        yield last_input_time


# 处理用户输入的函数
def chatbot(input_text, state, last_input_time):
    if input_text != "":
        state += f"User: {input_text}\n"
        last_input_time = asyncio.get_event_loop().time()

    return gr.update(value=state), last_input_time


# 初始化Gradio界面
with gr.Blocks() as demo:
    state = gr.State("")
    last_input_time = gr.State(asyncio.get_event_loop().time())  # 初始化最后输入时间

    chatbot_input = gr.Textbox(label="Chat with Bot", placeholder="Say something...")

    chatbot_output = gr.Textbox(label="Chatbot Response", interactive=False, lines=10)

    # 输入框的改变会触发聊天响应
    chatbot_input.submit(chatbot, inputs=[chatbot_input, state, last_input_time],
                         outputs=[chatbot_output, last_input_time])

    # 解决事件循环问题：启动后台异步任务
    demo.launch(inbrowser=True)

    # 使用 `asyncio.run()` 启动自动提交任务
    demo.queue().asyncio.run(auto_submit(state, last_input_time))