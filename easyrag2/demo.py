import gradio as gr

# vis.jsのカスタムHTMLとJavaScriptを定義
html_content = """
<!DOCTYPE html>
<html>
<head>
  <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js"></script>
  <link href="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.css" rel="stylesheet" type="text/css" />
</head>
<body>
  <div id="network" style="width: 600px; height: 400px; border: 1px solid lightgray;"></div>
  <script type="text/javascript">
    // ノードのデータセットを作成
    var nodes = new vis.DataSet([
      {id: 1, label: 'Node 1'},
      {id: 2, label: 'Node 2'},
      {id: 3, label: 'Node 3'},
      {id: 4, label: 'Node 4'},
      {id: 5, label: 'Node 5'}
    ]);

    // エッジのデータセットを作成
    var edges = new vis.DataSet([
      {from: 1, to: 3},
      {from: 1, to: 2},
      {from: 2, to: 4},
      {from: 2, to: 5}
    ]);

    // ネットワークを作成
    var container = document.getElementById('network');
    var data = {
      nodes: nodes,
      edges: edges
    };
    var options = {};
    var network = new vis.Network(container, data, options);
  </script>
</body>
</html>
"""

# Gradio Blocksインターフェースを定義
with gr.Blocks() as demo:
    gr.HTML(html_content)

# Gradioインターフェースを起動
demo.launch()