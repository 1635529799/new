from openai import OpenAI
from typing import List
import pandas as pd
import re
import difflib

def get_answer(client,question,answer,models):
    prompt = f"""请从以下文本下面的问题和答案中构建回答：
           1. 如果问题和答案都不为空
           要求：
            根据问题和答案构建回答，要求逻辑清晰，合理
           2.如果问题不为空，答案为空。
            联网查找答案，并且给出的答案逻辑清晰，合理
           3.答案和问题都没有
             回答输入问题不正确，请重新输入！
           4.回答精简，不要无关的东西，就回答答案啊
           问题：{question},答案：{answer}"""
    response = client.chat.completions.create(
        model=models,
        messages=[
            {"role": "system", "content": "你是一个专业的基于大语言模型与知识图谱融合的问答助手"},
            {"role": "user", "content": prompt}
        ]
    )

    full_text =  (
                response.choices[0].message.content or "")

    return full_text



MAX_CHUNK = 500  # 分块大小
OVERLAP = 50  # 重叠字符数


def fast_chunk_to_list(text: str) -> List[str]:
    """
    对一段文本做重叠分块（sliding window），返回字符串列表。
    保证每块长度不超过 MAX_CHUNK，相邻块之间有 OVERLAP 的重叠。
    """
    if MAX_CHUNK <= OVERLAP:
        raise ValueError("MAX_CHUNK 必须大于 OVERLAP")

    chunks = []
    buffer = text  # 直接把整个文本当缓冲区

    # 只要缓冲区长度够，就持续切分
    while len(buffer) >= MAX_CHUNK:
        # 取前 MAX_CHUNK 字符
        chunks.append(buffer[:MAX_CHUNK])
        # 保留最后 OVERLAP 字符，到下一个循环再继续拼接
        buffer = buffer[MAX_CHUNK - OVERLAP:]

    # 处理剩下的不足一块的尾部
    if buffer:
        chunks.append(buffer)

    return chunks


def call_tencent_api(chunk: str,client,models="deepseek-v3") -> dict:
    try:
        # print(chunk)
        prompt = f"""请从以下文本提取知识图谱信息：
        1. 识别关系：源实体、目标实体、关系类型
        格式要求：
        - 关系：("源实体|目标实体|关系类型)
        2.下面这种情况就提取中文，例如：污染源（Pollution Sources），只提取污染源作为实体，不提取括号里面的英文
        3.尽可能多的提取到关系
        4.输出保证是：("源实体|目标实体|关系类型)的格式
        5.输出文本直接给出关系，关系间分行，不要其他内容,只要关系
        文本内容：{chunk.replace(" ", "")}"""
        completion = client.chat.completions.create(
            model=models,
            messages=[
                {"role": "system", "content": "你是一个专业的知识图谱构建助手"},
                {"role": "user", "content": prompt}
            ]
        )

        result = parse_response(completion)
        print(result)
        # 添加原文验证信息
        for rel in result["relationships"]:
            rel["source_text"] = chunk
        return result
    except Exception as e:

        return {"entities": [], "relationships": []}


def parse_response(response) -> dict:
    relationships = []
    #     full_text = (response.choices[0].message.reasoning_content or "") + "\n" + (response.choices[0].message.content or "")
    full_text = response.choices[0].message.content

    for line in full_text.split('\n'):
        line = line.strip()
        parts = line.split('|')
        if len(parts) >= 3:
            relationships.append({
                "source": parts[0].strip().upper(),
                "target": parts[1].strip().upper(),
                "rel_type": parts[2].strip(),
            })
    return {"relationships": relationships}


def fuzzy_contains(sentence, entity, threshold=0.8):
    """
    判断 sentence 中是否存在与 entity 相似度超过 threshold 的子串，
    如果存在，返回 True；否则返回 False。
    先判断精确包含，再采用滑动窗口进行模糊匹配。
    """
    # 精确匹配直接返回 True
    if entity in sentence:
        return True
    n = len(entity)
    # 尝试长度在 [n-1, n+1] 范围内的子串匹配
    for length in range(max(n-1, 1), n+2):
        for i in range(0, len(sentence) - length + 1):
            substr = sentence[i:i+length]
            ratio = difflib.SequenceMatcher(None, entity, substr).ratio()
            if ratio >= threshold:
                return True
    return False

def extract_entity_relation_context(text, entity1, entity2, threshold=0.7):
    """
    从文本中提取包含两个目标实体（entity1 和 entity2）的完整上下文。
    - 如果两实体在同一句中（模糊匹配），则返回该完整句子；
    - 否则返回包含两者的最小连续句块。
    """
    # 按中文句号、问号、感叹号分割文本，并保留句子结束符
    sentences = re.split(r'(?<=[。！？])', text)
    sentences = [s.strip() for s in sentences if s.strip()]  # 去除空白

    # 优先查找同时包含两个实体的句子（采用模糊匹配）
    for sentence in sentences:
        if fuzzy_contains(sentence, entity1, threshold) and fuzzy_contains(sentence, entity2, threshold):
            return sentence

    # 分别记录包含 entity1 与 entity2 的句子索引（模糊匹配）
    indices_entity1 = [i for i, s in enumerate(sentences) if fuzzy_contains(s, entity1, threshold)]
    indices_entity2 = [i for i, s in enumerate(sentences) if fuzzy_contains(s, entity2, threshold)]

    # 如果任一实体都未出现，则返回 None
    if not indices_entity1 or not indices_entity2:
        return text

    # 寻找最小的连续句子块，该块中两实体分别出现（模糊匹配）
    best_start, best_end = None, None
    best_length = float('inf')
    for i in indices_entity1:
        for j in indices_entity2:
            start = min(i, j)
            end = max(i, j)
            length = end - start + 1
            if length < best_length:
                best_length = length
                best_start, best_end = start, end

    context_block = ''.join(sentences[best_start:best_end+1])
    return context_block


# 提取文本中的三元组
def get_triples(client,text,file_name):
    text_chunks = fast_chunk_to_list(text)
    # print(f"总块数：{len(text_chunks)}")

    all_relationships = []

    for chunk in text_chunks:
        result=call_tencent_api(chunk,client)
        all_relationships.extend(result["relationships"])

    if all_relationships:
        df = pd.DataFrame(all_relationships).drop_duplicates(
            subset=['source', 'target', 'rel_type', 'source_text']
        )
        df['label'] = file_name

        df['rel_type'] = df['rel_type']
        df['开始节点类型'] = df['label'].apply(lambda x: re.sub(r"[^\u4e00-\u9fff]", "", x))
        df['结束节点类型'] = df['label'].apply(lambda x: re.sub(r"[^\u4e00-\u9fff]", "", x))
        df['开始节点'] = df['source'].apply(lambda x: re.sub(r"[^\u4e00-\u9fff]", "", x))
        df['结束节点'] = df['target'].apply(lambda x: re.sub(r"[^\u4e00-\u9fff]", "", x))
        df['关系'] = df['rel_type'].apply(lambda x: re.sub(r"[^\u4e00-\u9fff]", "", x))
        # 开始节点，结束节点，关系，都只提取长度小于20的
        df = df[~df.apply(lambda row: any(len(row[col]) > 20 for col in ['开始节点', '关系', '结束节点']), axis=1)]

        df = df.drop_duplicates(
            subset=['开始节点', '关系', '结束节点'],  # 指定要判断重复的列
            keep='first'  # 保留第一个出现的重复项
        )
        df['文本'] = df.apply(
            lambda x: extract_entity_relation_context(x['source_text'], x['开始节点'], x['结束节点']),
            axis=1
        )
        df = df[['开始节点', '开始节点类型', '关系', '结束节点', '结束节点类型', "文本"]]
        df = df.dropna()
        print(df)
        return df
    else:
        return None




