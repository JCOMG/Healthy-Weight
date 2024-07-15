import json
from datasets import load_dataset, Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

# 加載數據集
with open('intents.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 構建Dataset
dataset = Dataset.from_dict(data)

# 載入預訓練模型和分詞器
model_name = "llama3-8b-8192"
model = AutoModelForCausalLM.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# 編碼數據
def tokenize_function(examples):
    return tokenizer(examples['patterns'], padding='max_length', truncation=True)

tokenized_datasets = dataset.map(tokenize_function, batched=True)

# 設置訓練參數
training_args = TrainingArguments(
    output_dir='./results',          
    num_train_epochs=3,              
    per_device_train_batch_size=4,   
    per_device_eval_batch_size=4,    
    warmup_steps=500,                
    weight_decay=0.01,               
    logging_dir='./logs',            
    logging_steps=10,
)

# 定義 Trainer
trainer = Trainer(
    model=model,                         
    args=training_args,                  
    train_dataset=tokenized_datasets['train'], 
    eval_dataset=tokenized_datasets['eval']  
)

# 開始訓練
trainer.train()
