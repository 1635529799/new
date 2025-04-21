# 标注实体，结巴分词的时候可以显示出来
import pandas as pd
import numpy as np
import pickle
from myneo4j.views import *

# client = OpenAI(
#     api_key="sk-7ca946c7053e4a5a8d3849f7659bc80a",
#     base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
# )

def to_va():
    df=pd.read_csv("result.csv")
    df.dropna(axis=0, how='any', inplace=True)
    file=open("entitys.txt","w",encoding='utf-8')

    lines=set()
    relations=set()
    for i, j in df.iterrows():

        head = j['开始节点']
        lines.add(head)

        relation=j['关系']
        relations.add(relation)

    for line in set(lines):
        if len(line)==0:
            continue
        line=line+" " + "15" + " " + "nm" + '\n'
        file.write(line)
    questions=lines
    en=pd.DataFrame()
    en['en']=list(questions)
    en.to_csv("questions.csv",index=False)


# 获取向量维度进行相似度语义匹配
def get_emb():
    questions, list_embs = get_datas(client)
    # 保存到 .npy 文件
    np.save('embeddings.npy',list_embs)
    with open("questions.pkl", "wb") as f:
        pickle.dump(questions, f)
    print(questions)

def embs():
    loaded_embs = np.load('./datas/embeddings.npy')
    return loaded_embs

def get_ents():
    df1 = pd.read_csv("./datas/questions.csv")

    q = df1['en'].values.tolist()

    return q

if __name__ == '__main__':
    to_va()
    get_emb()