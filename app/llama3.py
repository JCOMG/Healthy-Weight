import json

from groq import Groq


class GroqChatClient:
    def __init__(self, model_id="llama3-8b-8192", system_message=None,
                 api_key="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"):

        if api_key:
            self.client = Groq(api_key=api_key)
        else:
            self.client = Groq()

        self.model_id = model_id

        self.messages = []

        if system_message:
            self.messages.append({'role': 'system', 'content': system_message})



    def draft_message(self, prompt, role='user'):
        return {'role': role, 'content': prompt}


    def send_request(self, message, temperature=0.5, max_tokens=1024, stream=False, stop=None):
        self.messages.append(message)

        chat_completion = self.client.chat.completions.create(
            messages=self.messages,
            model=self.model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            stop=stop

        )
        if not stream:
            response = {
                'content': chat_completion.choices[0].message.content,
                'finish_reason': chat_completion.choices[0].finish_reason,
                'role': chat_completion.choices[0].message.role,
                'prompt_tokens': chat_completion.usage.prompt_tokens,
                'prompt_time': chat_completion.usage.prompt_time,
                'completion_tokens': chat_completion.usage.prompt_time,
                'completion_time': chat_completion.usage.completion_time,
                'total_tokens': chat_completion.usage.total_tokens,
                'total_time': chat_completion.usage.total_time
            }
            self.messages.append(self.draft_message(response['content'], response['role']))
            return response
        return chat_completion

    @property
    def last_message(self):
        return self.messages[-1]


    def fine_tune(self, intents):
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
