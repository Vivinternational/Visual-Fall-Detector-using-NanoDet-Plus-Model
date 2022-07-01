import torch
import onnx
import onnxruntime
import argparse
import time
import numpy as np

from onnx import helper as h
from onnx import checker as ch
from onnx import TensorProto
from onnx import numpy_helper as nph
from collections import OrderedDict

def main(model_path, output_path):
    fix_onnx_resize_nodes(model_path, output_path)

def save_new_model(opset_version, nodes, graph, out_path, verbose=True):
    if verbose:
        print("Creating new fixed graph...")
    # * create a new graph with new nodes.
    new_graph = h.make_graph(
        nodes,
        graph.name,
        graph.input,
        graph.output,
        initializer=graph.initializer,  # The initializer holds all non-constant weights.
    )
    if verbose:
        print("Creating new fixed model...")
    new_model = h.make_model(new_graph, producer_name="onnx-fix-nodes")
    new_model.opset_import[0].version = opset_version
    ch.check_model(new_model)
    if verbose:
        print(f"Saving new model as: {out_path}")
    onnx.save_model(new_model, out_path)


def fix_onnx_resize_nodes(model_path: str, out_path: str, verbose=True):
    """
    Method to fix resize nodes giving the following error in Tensorflow
    conversions:
    - "Resize coordinate_transformation_mode=pytorch_half_pixel is not supported in Tensorflow"
    """
    if verbose:
        print(f"Loading Model: {model_path}")
    # * load model.
    model = onnx.load_model(model_path)
    ch.check_model(model)
    # * get model opset version.
    opset_version = model.opset_import[0].version
    graph = model.graph

    new_nodes = []
    if verbose:
        print("Fixing Resize nodes...")
    for i, node in enumerate(graph.node):
        if node.op_type == "Resize":
            new_resize = onnx.helper.make_node(
                'Resize',
                inputs=node.input,
                outputs=node.output,
                name=node.name,
                coordinate_transformation_mode='half_pixel',  # Instead of pytorch_half_pixel, unsupported by Tensorflow
                mode='linear',
            )
            # Update node
            new_nodes += [new_resize]
        else:
            new_nodes += [node]

    save_new_model(opset_version=opset_version, graph=graph, nodes=new_nodes,
                   out_path=out_path, verbose=verbose)

def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Fix pytorch_half_pixel error for Tensorflow conversion.",
    )
    parser.add_argument(
        "--model_path", type=str, default=None, help="Path to onnx converted model."
    )
    parser.add_argument(
        "--out_path", type=str, default=None, help="Path to onnx model after node fix."
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    model_path = args.model_path
    out_path = args.out_path
    main(model_path, out_path)
    print("Model saved to:", out_path)
