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

    def fine_tune(self, intents):
        # 這裡加入處理您的意圖數據集的邏輯
        for intent in intents:
            for pattern in intent["patterns"]:
                self.messages.append(self.draft_message(pattern, 'user'))
                self.messages.append(self.draft_message(intent["responses"][0], 'assistant'))


if __name__ == '__main__':
    system_message = """you are an healthy assistant help people to make their life better.
    people who wants to lose weight give them some tips or people who wants to gain weight give them some tips. 
    people who wants to gain some healthy knowledge give them some advice.
    people who is struggling with not lose weight enough or gian weight enough give them some emotional support. 
    """.strip().replace('\n', '')
    client = GroqChatClient(model_id="llama3-8b-8192", system_message=system_message)
    stream_response = True

    with open('intents.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    client.fine_tune(data['intents'])

    while True:
        user_input = input("enter your message (or type 'exit','leave','stop',to end ): ")
        if user_input.lower() in ('exit', 'leave', 'stop'):
            break

        response = client.send_request(client.draft_message(user_input), stream=stream_response)

        message = ''
        for chunk in response:
            content_chunk = chunk.choices[0].delta.content
            print(content_chunk, end="")
            message += str(content_chunk)
        client.messages.append(client.draft_message(message, 'assistant'))
