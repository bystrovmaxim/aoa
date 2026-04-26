from graph.aggregation_graph_edge import AggregationGraphEdge
from graph.association_graph_edge import AssociationGraphEdge
from graph.composition_graph_edge import CompositionGraphEdge
from graph.edge_relationship import AGGREGATION, ASSOCIATION, COMPOSITION


def test_composition_graph_edge_uses_composition_relationship() -> None:
    edge = CompositionGraphEdge(
        edge_name="aspect",
        is_dag=False,
        source_node_id="pkg.Action",
        source_node_type="Action",
        target_node_id="pkg.Action:aspect",
        target_node_type="RegularAspect",
    )

    assert edge.edge_relationship is COMPOSITION


def test_aggregation_graph_edge_uses_aggregation_relationship() -> None:
    edge = AggregationGraphEdge(
        edge_name="params",
        is_dag=False,
        source_node_id="pkg.Action",
        source_node_type="Action",
        target_node_id="pkg.Action.Params",
        target_node_type="Params",
    )

    assert edge.edge_relationship is AGGREGATION


def test_association_graph_edge_uses_association_relationship() -> None:
    edge = AssociationGraphEdge(
        edge_name="domain",
        is_dag=True,
        source_node_id="pkg.Action",
        source_node_type="Action",
        target_node_id="pkg.Domain",
        target_node_type="Domain",
    )

    assert edge.edge_relationship is ASSOCIATION
