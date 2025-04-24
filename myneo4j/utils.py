import pandas as pd
import warnings
warnings.filterwarnings("ignore")
import json
import numpy as np
import faiss
from datas.pyneo_utils import *
from datas.entity_dict import get_ents,embs
from .LLM import get_answer

def get_datas(client):

    df1 = pd.read_csv("questions.csv")

    q = df1['en'].values.tolist()

    list_embs=init_wend(q,client)
    return q,list_embs

def get_embedding(text,client):
        """
        调用通义千问 API 获取文本向量，
        返回一个 1024 维的浮点数列表。
        """
        completion = client.embeddings.create(
            model="text-embedding-v3",
            input=text,
            dimensions=1024,
            encoding_format="float"
        )
        # 使用 model_dump_json() 方法获取 JSON 格式的响应
        json_str = completion.model_dump_json()
        # 将 JSON 转换为字典结构
        data = json.loads(json_str)
        embedding = data.get("data", [{}])[0].get("embedding")
        return embedding
def init_wend(list_texts,client):
    # 获取列表中文本的向量
    list_embeddings = [get_embedding(text,client) for text in list_texts]

    list_emb_np = np.array(list_embeddings)

    return list_emb_np


def get_entitys(text,client,list_embs,list_texts):
    list_embs = list_embs.astype('float32')
    faiss.normalize_L2(list_embs)

    # 2. 构建索引（这里用 IndexFlatIP，度量方式为内积）
    d = list_embs.shape[1]
    index = faiss.IndexFlatIP(d)
    index.add(list_embs)

    # 3. 对单条输入做同样的归一化
    input_embedding = np.array(get_embedding(text, client), dtype='float32').reshape(1, -1)
    faiss.normalize_L2(input_embedding)

    k = 1
    D, I = index.search(input_embedding, k)

    # 4. 取出最相似的文本并判断阈值
    best_sim = D[0][0]
    best_idx = I[0][0]
    threshold = 0.7

    if best_sim >= threshold:
        best_text = list_texts[best_idx]
    else:
        best_text = None

    print("最大相似度：", best_sim)
    print("匹配文本：", best_text)

    return best_text

def to_neo4j(df):
    g = Graph("bolt://localhost:7687", user="neo4j", password="123456")
    df.columns = ['开始节点', '开始节点类型', '关系', '结束节点', '结束节点类型', "文本"]

    for index, row in df.iterrows():
        try:
            start_name = row["开始节点"]
            start_type = row["开始节点类型"]
            relation = row["关系"]
            end_name = row["结束节点"]
            end_type = row["结束节点类型"]
            text = row['文本']

            start_obj = get_node_by_name(g, start_type, start_name)
            if start_obj == None:
                start_obj = Node(start_type,
                                 name=start_name
                                 )
                g.create(start_obj)
            # =====
            end_obj = get_node_by_name(g, end_type, end_name)
            if end_obj == None:
                end_obj = Node(end_type,
                               name=end_name,
                               text=text
                               )
                g.create(end_obj)
            rel = Relationship(start_obj, relation, end_obj)
            g.create(rel)
        except:
            continue


# 数据导入图谱,数据导入实体库、存储数据库，向量数据库生成
def service_upload(df, client):
    to_neo4j(df)
    print("图谱导入成功!")

    # 存储文件
    df_base = pd.read_csv("./datas/result.csv")
    data = pd.concat([df_base, df], axis=0, ignore_index=True)
    data = data.drop_duplicates()
    data.to_csv("./datas/result.csv", index=False)

    # 更新问题数据
    df_qbase = pd.read_csv("./datas/questions.csv")
    q = df['开始节点'].dropna().astype(str).tolist()
    en = pd.DataFrame({'en': list(set(q))})
    data_q = pd.concat([df_qbase, en], axis=0, ignore_index=True)
    data_q.to_csv("./datas/questions.csv", index=False)

    # 更新向量数据
    questions = list(en['en'])
    ems = embs()
    add_embs = init_wend(questions, client)
    all_embs = np.concatenate((ems, add_embs), axis=0)
    np.save('./datas/embeddings.npy', all_embs)

    # 实体库导入
    file = open("./datas/entitys.txt", "w", encoding='utf-8')
    lines = set()
    for _, j in data.iterrows():
        head = j.get('开始节点', "")
        if not isinstance(head, str):
            head = str(head)
        lines.add(head)

    for line in lines:
        if not isinstance(line, str):
            line = str(line)
        if len(line.strip()) == 0:
            continue
        file.write(line + " 15 nm\n")



def get_answers(entity,flag,client,key,g):


    s=set()
    if (entity != "") & (entity != None):
        sql = "MATCH (n)-[r]->(b) where n.name='%s' RETURN r,b" % (entity)
        # print(sql)
        nodes_data_all = g.run(sql).data()
        mnjh = ""
        mn = ""
        if len(nodes_data_all) > 0:
            for nodes_relations in nodes_data_all:
                node_dict = dict(nodes_relations['b'])
                mnjh = mnjh + node_dict["text"] + "；"
                s.add(node_dict["text"])
                r = str(nodes_relations['r']).split(":")[1].split("{")[0].strip()
                mn = mnjh + r + ":" + node_dict["name"] + " "
        daan = mn + mnjh
        text=' '.join([elem for elem in s])
        # text=text.replace("{","").replace("}","")
        # print(text)
        if (flag != True):
            key = key + "注意：问题中进行了实体扩充，更正，用扩充和更正的实体回答，正确的实体是：" + entity
    else:
        text=None
        daan = "暂时不支持此类问题，可以试试问：实体+关系问答模式(例如：土壤理化特性包含的特性指标有那些？)"
    daan = get_answer(client, key, daan, "deepseek-v3")



    return daan,text







if __name__ == '__main__':
    get_entitys()





