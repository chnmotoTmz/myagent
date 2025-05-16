import argparse
import gradio as gr
from gradio.components import Dropdown
from core import predict_with_model,keitaiso,load_data_from_file
from core import upload_file, upload_and_train, make_prediction,load_data_from_file
from model import create_database, delete_model
import networkx as nx
import gradio as gr
from model import load_model, get_model_list, delete_model, model_exists, get_network_relations,load_network_from_database
from core import upload_and_train, get_top_words,predict_with_model
from network import generate_network,get_related_nodes
import matplotlib.pyplot as plt
from model import get_network_relations,get_network_nodes
import pandas as pd
from model import get_network_relations
import matplotlib.pyplot as plt
import networkx as nx
import pdb


def predict_and_format(query_text, instruction_text, top_n=5):
    try:
        G, similarities = load_network_from_database()
        
        # Get only the models that are present in the network
        models = set(node.split(':')[0] for node in G.nodes())
        
        result = f"指示内容:\n{instruction_text}\n\nクエリ内容:\n{query_text}\n\n補足情報:\n"

        for index, model_name in enumerate(models, start=1):
            vectorizer, tfidf_matrix, df = load_model(model_name)
            
            if vectorizer is None or tfidf_matrix is None:
                continue
           
            closest_entries = predict_with_model(query_text, vectorizer, tfidf_matrix, top_n=1)
            if not closest_entries or (len(closest_entries) == 1 and closest_entries[0] == (0, 0.0)):
                continue

            doc_index, similarity = closest_entries[0]
            start_node = f"{model_name}:{doc_index}"
            
            result += f"\nModel {index}: {model_name}\n"
            result += f"起点ノード: {start_node}\n"
            result += f"類似度スコア: {similarity:.4f}\n"
            result += f"TEXT: {df.iloc[doc_index]['Column1']}\n"
            
            related_nodes = get_related_nodes(G, start_node, top_n)
            result += "関連ノード:\n"
            for node, weight in related_nodes:
                model, idx = node.split(':')
                idx = int(idx)
                _, _, related_df = load_model(model)
                text = related_df.iloc[idx]['Column1']
                result += f"  - {node} (類似度: {weight:.4f})\n    TEXT: {text}\n"
        
        return result
    except Exception as e:
        return f"Error occurred: {str(e)}"
    

    

#def update_model_lists():
    models = get_model_list()
    return Dropdown(choices=models), Dropdown(choices=models), Dropdown(choices=models)

def update_dropdown(models):
    return gr.update(choices=models, value=models[0] if models else None)

def get_node_relations(node, min_weight):
    relations = get_network_relations(node, min_weight)
    return relations

def plot_relations(relations):
    return None

def update_node_list():
    return gr.Dropdown.update(choices=get_model_list())


def plot_network(relations):
    G = nx.Graph()
    for node1, node2, weight in relations:
        G.add_edge(node1, node2, weight=weight)
    
    pos = nx.spring_layout(G)
    plt.figure(figsize=(10, 8))
    nx.draw(G, pos, with_labels=True, node_color='lightblue', 
            node_size=500, font_size=10, font_weight='bold')
    
    edge_labels = nx.get_edge_attributes(G, 'weight')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
    
    plt.title("Network Visualization")
    return plt.gcf()

def plot_relations(relations):
    G = nx.Graph()
    for relation in relations:
        node1, node2, weight = relation
        G.add_edge(node1, node2, weight=weight)
    
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, node_color='lightblue',
            node_size=500, font_size=8, font_weight='bold')
    
    # Update label formatting if needed
    labels = {node: node.replace(':', '\n') for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=8)
    
    edge_labels = nx.get_edge_attributes(G, 'weight')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
    plt.title("Node Relations")
    return plt.gcf()


# on_row_click 関数も適宜修正
def on_row_click(evt: gr.SelectData):
    selected_column = evt.index[1]  # 選択された列のインデックス
    if selected_column in [0, 1]:  # Node 1 または Node 2 の列がクリックされた場合
        node = evt.value
        top_words = get_top_words(node,30)
        if isinstance(top_words[0], str):  # エラーメッセージの場合
            return top_words[0]
        formatted_words = ", ".join([f"{word} ({score:.4f})" for word, score in top_words])
        return f"Top 10 words for {node}: {formatted_words}"
    else:
        return "Please click on a node column (Node 1 or Node 2)"

def read_file_and_generate_text(file):
    if file is not None:
        file_path = file.name
        try:
            # ファイルの内容を読み込む
            with open(file_path, 'r', encoding='utf-8') as f:
                generated_text = f.read()
            return generated_text
        except Exception as e:
            return f"ファイルの読み込みエラー: {str(e)}"
    return ""


def setup_gradio_interface():
    with gr.Blocks() as iface:
        with gr.Tab("Upload and Train"):
            upload_file_input = gr.File(label="Upload File")
            model_name_input = gr.Textbox(label="Model Name")
            description_input = gr.Textbox(label="Model Description")
            upload_output = gr.Textbox(label="Upload Result")
            upload_btn = gr.Button("Upload and Train")
            
            model_list = gr.Dropdown(label="Existing Models", choices=get_model_list())
            delete_btn = gr.Button("Delete Model")
            delete_output = gr.Textbox(label="Delete Result")



        with gr.Tab("Generate Network"):
            network_model_list = gr.Dropdown(label="Select Models for Network", choices=get_model_list(), multiselect=True)
            generate_btn = gr.Button("Generate Network")
            network_output = gr.Textbox(label="Generation Result")

        with gr.Tab("Network Relations"):
            with gr.Row():
                node_input = gr.Dropdown(label="Node Name", choices=get_network_nodes())
                min_weight_input = gr.Number(label="Minimum Weight", value=0.0, step=0.1)
            
            relations_btn = gr.Button("Get Relations")
            
            relations_output = gr.DataFrame(
                headers=["Node 1", "Node 2", "Weight"],
                label="Network Relations",interactive=False
            )

            top_words_output = gr.Textbox(label="Top 10 Words")

        def upload_and_analyze(file):
            if file is None:
                return None, None, None, "No file uploaded."
            
            df, default_model_name, default_description = upload_file(file)
            
            if df is not None:
                # 元のテキストを表示
                original_df = pd.DataFrame({"Text": df["Column1"]})
                
                # 形態素解析を実行
                analyzed_texts = keitaiso(df["Column1"].tolist())
                analyzed_df = pd.DataFrame({"Tokens": analyzed_texts})
                
                return original_df, analyzed_df, default_model_name, default_description
            else:
                return None, None, None, "Failed to load file."
            

        def update_network_relations(node, min_weight):
            relations = get_network_relations(node, min_weight)
            
            if not relations:
                return pd.DataFrame()
            
            # DataFrameの更新
            df_data = pd.DataFrame(relations, columns=["Node 1", "Node 2", "Weight"])
    
            return df_data

        with gr.Tab("Text Analysis"):
            instruction_file_input = gr.File(label="Upload Instruction File")
            instruction_input = gr.Textbox(label="Instruction Text", placeholder="Enter any special instructions...")
            query_file_input = gr.File(label="Upload Query File")
            query_input = gr.Textbox(label="Query Text", placeholder="Enter text here...")
            top_n_input = gr.Number(label="Top N", value=10, step=1)
        
            predict_btn = gr.Button("Submit")
            prediction_output = gr.Textbox(label="Prediction Result")


        predict_btn.click(
            fn=predict_and_format,
            inputs=[query_input, instruction_input, top_n_input],
            outputs=[prediction_output]
        )


        with gr.Tab("Morphological Analysis"):
            with gr.Row():
                with gr.Column():
                    text_input = gr.Textbox(label="Enter Text", lines=5, placeholder="Enter text here...")
                    file_input = gr.File(label="Or Upload Text File")
                
                analyze_btn = gr.Button("Analyze")

            with gr.Row():
                original_text = gr.Dataframe(label="Original Text", headers=["Text"])
                analyzed_text = gr.Dataframe(label="Analyzed Text", headers=["Tokens"])

        def analyze_text(text, file):

            if file:
                try:
                    file_path = file.name    
                    df = load_data_from_file(file_path)
                    texts = df["Column1"].tolist()
                except:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            texts = f.readlines()
                    except:
                        return None, None, "Failed to read the file."
            elif text:
                texts = [text]
            else:
                return None, None, "No text or file provided."
            
            original_df = pd.DataFrame({"Text": texts})
            analyzed_texts = keitaiso(texts)
            analyzed_df = pd.DataFrame({"Tokens": [''.join(tokens) for tokens in analyzed_texts]})
            
            return original_df, analyzed_df, "Analysis completed."

        analyze_btn.click(
            analyze_text,
            inputs=[text_input, file_input],
            outputs=[original_text, analyzed_text, gr.Textbox(label="Status")]
        )

        def upload_and_update(*args):
            file, model_name, description = args
            if model_exists(model_name):
                if not gr.Button("Model already exists. Click to overwrite.").click():
                    return (f"Upload cancelled. Model '{model_name}' was not overwritten.",
                        update_dropdown(get_model_list()),
                        update_dropdown(get_model_list()))
            result = upload_and_train(*args)
            models = get_model_list()
            return (result[0],
                update_dropdown(models),
                update_dropdown(models))

        def delete_and_update(model_name):
            result = delete_model(model_name)
            models = get_model_list()
            return (result[0],
                    update_dropdown(models),
                    update_dropdown(models))


        upload_btn.click(
            upload_and_update,
            inputs=[upload_file_input, model_name_input, description_input],
            outputs=[upload_output, model_list, network_model_list]
        )

        delete_btn.click(
            delete_and_update,
            inputs=[model_list],
            outputs=[delete_output, model_list, network_model_list]
        )

        upload_file_input.change(
            upload_file,
            inputs=[upload_file_input],
            outputs=[gr.State(), model_name_input, description_input]
        )

        def generate_network_and_update(model_names):
            result = generate_network(model_names)
            updated_nodes = get_network_nodes()
            return result, gr.update(choices=updated_nodes)

        generate_btn.click(
            fn=generate_network_and_update,
            inputs=[network_model_list],
            outputs=[network_output, node_input]
        )

        relations_btn.click(
            update_network_relations,
            inputs=[node_input, min_weight_input],
            outputs=[relations_output]
        )

        relations_output.select(
            on_row_click,
            None,
            top_words_output
        )

        # ファイルアップロード時にinstruction_inputを更新
        instruction_file_input.change(
            read_file_and_generate_text,
            inputs=[instruction_file_input],
            outputs=[instruction_input]
        )

        # ファイルアップロード時にquery_inputを更新
        query_file_input.change(
            read_file_and_generate_text,
            inputs=[query_file_input],
            outputs=[query_input]
        )

        predict_btn.click(
            fn=predict_and_format,
            inputs=[query_input, instruction_input, top_n_input],
            outputs=[prediction_output]
        )
    return iface

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Gradio interface with custom port")
    parser.add_argument('--port', type=int, default=7861, help='Port to run the server on')
    args = parser.parse_args()

    create_database()
    interface = setup_gradio_interface()
    interface.launch(share=False, server_name="0.0.0.0", server_port=args.port, show_api=False)
    
