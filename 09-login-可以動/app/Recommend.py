import json
from datasets import load_dataset
from groq import Groq
from transformers import Trainer, TrainingArguments, AutoTokenizer, AutoModelForCausalLM, \
    DataCollatorForLanguageModeling

# 加载营养数据集
ds = load_dataset("sarthak-wiz01/nutrition_dataset")


class GroqChatClient:
    def __init__(self, model_id="llama3-8b-8192", system_message=None,
                 api_key="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"):
        if api_key:
            self.client = Groq(api_key=api_key)
        else:
            self.client = Groq()

        self.model_id = model_id
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForCausalLM.from_pretrained(model_id)
        self.tokenizer.pad_token = self.tokenizer.eos_token
        self.messages = []

        if system_message:
            self.messages.append({'role': 'system', 'content': system_message})

    def draft_message(self, prompt, role='user'):
        return {'role': role, 'content': prompt}

    def send_request(self, message, temperature=0.5, max_tokens=1024, stream=False, stop=None):
        self.messages.append(message)
        inputs = self.tokenizer([m['content'] for m in self.messages], return_tensors='pt', padding=True,
                                truncation=True)
        outputs = self.model.generate(inputs['input_ids'], max_length=max_tokens, temperature=temperature)
        content = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        response = {
            'content': content,
            'role': 'assistant'
        }

        self.messages.append(self.draft_message(response['content'], response['role']))
        return response

    @property
    def last_message(self):
        return self.messages[-1]

    def fine_tune(self, dataset, epochs=3):
        # 转换数据集格式以用于微调
        def preprocess_function(examples):
            # 将所需字段拼接成一个字符串
            combined_text = []
            for i in range(len(examples['Breakfast Suggestion'])):
                text = (
                        examples['Breakfast Suggestion'][i] + " " +
                        examples['Lunch Suggestion'][i] + " " +
                        examples['Dinner Suggestion'][i] + " " +
                        examples['Snack Suggestion'][i]
                )
                combined_text.append(text)
            return self.tokenizer(combined_text, padding='max_length', truncation=True)

        tokenized_datasets = dataset.map(preprocess_function, batched=True)

        # 使用train-test split来分割数据集
        train_test_split = tokenized_datasets['train'].train_test_split(test_size=0.2)
        train_dataset = train_test_split['train']
        test_dataset = train_test_split['test']

        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False,
        )

        training_args = TrainingArguments(
            output_dir='./results',
            num_train_epochs=epochs,
            per_device_train_batch_size=2,
            per_device_eval_batch_size=2,
            warmup_steps=500,
            weight_decay=0.01,
            logging_dir='./logs',
            logging_steps=10,
            evaluation_strategy="steps",
            eval_steps=50,
            save_steps=100,
        )

        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=test_dataset,
            data_collator=data_collator,
            device='cpu'
        )

        trainer.train()
        self.model.save_pretrained('./trained_model')
        self.tokenizer.save_pretrained('./trained_model')


if __name__ == '__main__':
    system_message = """你是一个健康助手，帮助人们改善生活。想要减肥的人提供一些建议，想要增重的人提供一些建议。
    想要获取健康知识的人提供一些建议。纠结于无法减重或增重的人提供一些情感支持。""".strip().replace('\n', '')
    client = GroqChatClient(model_id="gpt2", system_message=system_message)

    # 微调模型
    client.fine_tune(ds)

    # 示例用户输入的健康目标
    user_goal = "減肥"
    user_input = f"根據用戶的健康目標 {user_goal}，請推薦一些適合的食物。"

    response = client.send_request(client.draft_message(user_input))

    print("Recommended foods:")
    print(response['content'])
