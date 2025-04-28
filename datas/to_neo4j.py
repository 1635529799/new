from datas.pyneo_utils import *
import os
import csv
import pandas as pd

g = Graph("bolt://localhost:7687", user="neo4j", password="123456")
# g = Graph('http://localhost:7474', user='neo4j', password='123456')

cypher = 'MATCH (n) OPTIONAL MATCH (n)-[r]-() DELETE n,r'
g.run(cypher)

df=pd.read_csv("result.csv")
df.columns=['开始节点','开始节点类型','关系','结束节点','结束节点类型',"文本"]
print(df)
# df.to_csv("kg.csv",index=False)

for index,row in df.iterrows():
   try:
        start_name = row["开始节点"]
        start_type = row["开始节点类型"]
        relation = row["关系"]
        end_name = row["结束节点"]
        end_type = row["结束节点类型"]
        text=row['文本']
        print(row)

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

