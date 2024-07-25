import json

from groq import Groq


class GroqChatClient:
    def __init__(self, model_id="llama3-8b-8192", system_message=None,
                 api_key="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"):
        # system_message is a prompt
        # Prompt 的角色和功能
        # 提供上下文：Prompt 在對话系统中设定了开始對話时的场景，讓模型了解它所處的對話環境和角色定位。
        # 指導產生：基於提供的 prompt，模型將產生符合場景需求的回應，這在客製化的聊天機器人中為重要，如健康助理、客服機器人等。
        # 增強相關性和準確性：透過精確的 prompt 設定，可以顯著提高模型回答的相關性和準確性，確保它提供的資訊對使用者真正有幫助。
        if api_key:
            self.client = Groq(api_key=api_key)
        else:
            self.client = Groq()
        # 如果有提供 api_key（即 api_key 為真），則使用該 api_key 來初始化 Groq 客戶端：self.client = Groq(api_key=api_key)。
        # 如果沒有提供 api_key（即 api_key 為假），則初始化不使用 api_key 的 Groq 客戶端：self.client = Groq()。
        self.model_id = model_id

        self.messages = []

        if system_message:
            self.messages.append({'role': 'system', 'content': system_message})

        # 其中 role 設置為 'system'，表示這是一條系統消息；content 設置為 system_message，即系統消息的內容。
        # 初始化後是長這樣 [
        #     {'role': 'system', 'content': '你是一个健康助手，帮助人们改善生活。想要减肥的人提供一些建议，想要增重的人提供一些建议。
        #     想要获取健康知识的人提供一些建议。纠结于无法减重或增重的人提供一些情感支持。'}
        # ]
        # 這樣做的目的是在對話開始時設置上下文，讓聊天機器人知道它的角色和應該如何提供幫助。

    def draft_message(self, prompt, role='user'):
        return {'role': role, 'content': prompt}

    # prompt：這是一個參數，表示訊息的內容。
    # role：這是另一個參數，表示訊息的角色。
    # 預設為 'user'，表示這則訊息是由使用者發送的。可設定為 'system' 或 'assistant'，分別表示系統訊息或助手回覆。
    def send_request(self, message, temperature=0.5, max_tokens=1024, stream=False, stop=None):
        self.messages.append(message)
        # temperature :　生成文本的隨機性　

        # 低 temperature : 0.1 ， 模型產生的文字可能非常保守，重複性較高，基本上總是選擇最高機率的單字：
        # Prompt: "今天的天氣"
        # Output: "今天的天氣很好，陽光明媚。"

        # 高 temperature : 1.0 ， 模型生成的文本可能更具創意和多樣性：
        # Prompt: "今天的天氣"
        # Output: "今天的天氣充滿了驚喜，微風拂面，雲層變幻莫測。"

        # 中 temperature : 0.5-0.7 ，產生的文字既不會過於單調，也不會太隨機，適合大多數一般性應用 :
        # Prompt: "今天的天氣"
        # Output: "今天的天氣非常好，有點微風，天空很藍。"

        # max_tokens = 機器人回應的文字的最大長度

        # stream=False 不啟用串流傳輸，用戶需要等待模型生成完整文章後才能看到結果

        # stream=True 在聊天機器人或線上客服系統中，用戶希望快速獲得回應。啟用串流後，用戶可以在模型生成完整回復之前逐步看到部分內容

        # stop=None 指定一個或多個停止標記可以確保產生的內容在遇到這些標記時會自動停止，從而避免產生過長或不相關的內容。
        chat_completion = self.client.chat.completions.create(
            messages=self.messages,
            model=self.model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            stop=stop

            # 這是呼叫 Groq 用戶端的 create 方法來建立一個聊天完成請求。這個方法會將請求傳送給模型，並傳回產生的結果。
        )
        if not stream:  # 現在的 stream = False
            response = {
                'content': chat_completion.choices[0].message.content,  # 模型生成的文本内容。
                'finish_reason': chat_completion.choices[0].finish_reason,
                # 產生結束的原因，可能的值包括 'stop'、'length' 等，指示產生是因為什麼原因停止的。
                'role': chat_completion.choices[0].message.role,
                # 消息的角色，通常是 'assistant'。
                'prompt_tokens': chat_completion.usage.prompt_tokens,
                'prompt_time': chat_completion.usage.prompt_time,
                # prompt_tokens：如果使用者輸入（“How is the weather today？”）所使用的token(標記數)是 5。
                # prompt_time：表示處理使用者的 token是 0.02 秒。
                'completion_tokens': chat_completion.usage.prompt_time,
                'completion_time': chat_completion.usage.completion_time,
                # completion_tokens : 機器人所回答的內容的字數
                'total_tokens': chat_completion.usage.total_tokens,  # 總標記數，包括提示(prompt_tokens)和完成(completion_tokens)部分。
                'total_time': chat_completion.usage.total_time
            }
            self.messages.append(self.draft_message(response['content'], response['role']))
            # 把機器人生成的回應append 在使用者的輸入的底下，這樣可以保持對話的上下文。
            return response
        return chat_completion

    @property
    def last_message(self):
        return self.messages[-1]

    #     #class Chat: 沒有property的時候
    #     def __init__(self):
    #         self.messages = []
    #
    #     def add_message(self, message):
    #         self.messages.append(message)
    #
    #     def get_last_message(self):
    #         return self.messages[-1]
    #
    # # 使用範例
    # chat = Chat()
    # chat.add_message("Hello")
    # chat.add_message("How are you?")

    # 獲取最後一個訊息
    # print(chat.get_last_message())  # 輸出: How are you?

    # #     class Chat: 有property的時候

#     class Chat:
#     def __init__(self):
#         self.messages = []
#
#     def add_message(self, message):
#         self.messages.append(message)
#
#     @property
#     def last_message(self):
#         return self.messages[-1]
#
#
# # 使用範例
# chat = Chat()
# chat.add_message("Hello")
# chat.add_message("How are you?")
#
# # 獲取最後一個訊息
# print(chat.last_message)  # 輸出: How are you?


    def fine_tune(self, intents): # 微調 llama3 model
        for intent in intents:
            for pattern in intent["patterns"]:
                self.messages.append(self.draft_message(pattern, 'user'))
                self.messages.append(self.draft_message(intent["responses"][0], 'assistant'))
                # 將每個intents的pattern作為用戶訊息，將相應的回應作為助手訊息，依次添加到 messages 列表中。
# 假如 :
#  intents = [
#     {
#         "patterns": ["Hello", "Hi", "Hey"],
#         "responses": ["Hello! How can I help you today?"]
#     },
#     {
#         "patterns": ["Bye", "Goodbye"],
#         "responses": ["Goodbye! Have a great day!"]
#     }
# ]
# client = GroqChatClient()
#
# client.fine_tune(intents)
#
# print(client.messages)

# [
#     {'role': 'user', 'content': 'Hello'},
#     {'role': 'assistant', 'content': 'Hello! How can I help you today?'},
#     {'role': 'user', 'content': 'Hi'},
#     {'role': 'assistant', 'content': 'Hello! How can I help you today?'},
#     {'role': 'user', 'content': 'Hey'},
#     {'role': 'assistant', 'content': 'Hello! How can I help you today?'},
#     {'role': 'user', 'content': 'Bye'},
#     {'role': 'assistant', 'content': 'Goodbye! Have a great day!'},
#     {'role': 'user', 'content': 'Goodbye'},
#     {'role': 'assistant', 'content': 'Goodbye! Have a great day!'}
# ]




if __name__ == '__main__':
    system_message = """you are an healthy assistant help people to make their life better.
    people who wants to lose weight give them some tips or people who wants to gain weight give them some tips. 
    people who wants to gain some healthy knowledge give them some advice.
    people who is struggling with not lose weight enough or gian weight enough give them some emotional support. 
    """.strip().replace('\n', '')
    # strip().replace('\n', '') 方法用來移除字符串首尾的空白字符（包括空格和換行符）。
    client = GroqChatClient(model_id="llama3-8b-8192", system_message=system_message)
    stream_response = True
    # 當 stream_response 設為 True 時，表示我們希望以串流的方式接收模型的回應，這意味著模型將會逐步返回回應，而不是等待整個回應生成完畢才返回。

    with open('intents.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    client.fine_tune(data['intents']) # 進入方法 fine_tune去做微調

    while True:
        user_input = input("enter your message (or type 'exit','leave','stop',to end ): ")
        if user_input.lower() in ('exit', 'leave', 'stop'):
            break

        response = client.send_request(client.draft_message(user_input), stream=stream_response)
        # 假設 user_input 是 "I want to lose weight, can you help me?"，那麼 draft_message 方法會生成一個訊息字典，類似這樣：
        # {
        #     'role': 'user',
        #     'content': 'I want to lose weight, can you help me?'
        # }

        # 然後使用 client.send_request() 方法發送請求給模型，並獲取回應。stream = stream_response 表示我們希望逐步接收回應內容。

        message = ''
        for chunk in response: #這是一個循環，用來處理逐步接收的回應內容（假設 stream_response 為 True）。
            content_chunk = chunk.choices[0].delta.content
            # chunk 是每次迭代得到的一個回應塊。
            # 每個 chunk 包含一個或多個選項（choices），這裡我們取第一個選項 choices[0]。
            # delta 是這個選項中的增量更新部分。增量更新的意思是每個回應塊只包含新生成的一部分內容，而不是整個回應。
            # content 是增量更新的具體內容，表示這個回應塊中新增的文字。
            # 這樣做的原因是因為當模型以串流的方式返回回應時，它會逐塊生成內容。每個回應塊只包含新增加的部分，而不是完整的回應。

            # ex :
            # response = [
            #     {"choices": [{"delta": {"content": "Hello"}}]},
            #     {"choices": [{"delta": {"content": ", how"}}]},
            #     {"choices": [{"delta": {"content": " are you"}}]},
            #     {"choices": [{"delta": {"content": " doing?"}}]}
            # ]
            # 第一個回應塊:
            # chunk = {"choices": [{"delta": {"content": "Hello"}}]}
            # content_chunk = chunk.choices[0].delta.content  # "Hello"
            # 第二個回應塊:
            # chunk = {"choices": [{"delta": {"content": ", how"}}]}
            # content_chunk = chunk.choices[0].delta.content  # ", how"
            # 第三個回應塊:
            # chunk = {"choices": [{"delta": {"content": " are you"}}]}
            # content_chunk = chunk.choices[0].delta.content  # " are you"
            # 第四個回應塊:
            # chunk = {"choices": [{"delta": {"content": " doing?"}}]}
            # content_chunk = chunk.choices[0].delta.content  # " doing?"

            print(content_chunk, end="") # 將提取的內容即時打印出來。end="" 表示打印內容後不換行
            message += str(content_chunk) # 將提取的內容追加到 message 字符串中，形成完整的回應。
        client.messages.append(client.draft_message(message, 'assistant'))
        # client.messages：這是一個列表，用來存儲所有的對話訊息，包括使用者的訊息和模型的回應。
        # 將生成的完整回應訊息（角色為 'assistant'）添加到 client.messages 列表中，這樣可以保留整個對話的上下文。
