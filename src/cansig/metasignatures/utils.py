from typing import List, Dict, Union
import anndata as ad  # pytype: disable=import-error
import pathlib as pl  # pytype: disable=import-error
import pandas as pd  # pytype: disable=import-error
import seaborn as sns  # pytype: disable=import-error
import scanpy as sc  # pytype: disable=import-error
import numpy as np  # pytype: disable=import-error
import matplotlib.pyplot as plt  # pytype: disable=import-error
import json  # pytype: disable=import-error
import umap  # pytype: disable=import-error
from sklearn.manifold import MDS  # pytype: disable=import-error

import cansig.plotting.plotting as plotting

# Retrieve signatures from directory


def get_runs_sig(basedir: pl.Path) -> Dict[str, List]:
    signatures = []
    integration_runs = []
    runs = []
    sig_index = []
    cluster_memb = []
    for i, path in enumerate(basedir.iterdir()):
        path = pl.Path(path)
        with open(path.joinpath("integration-settings.json"), "r") as f:
            data = json.load(f)

        if data not in integration_runs:
            integration_runs.append(data)

        n_run = integration_runs.index(data)

        cluster_memb.append(pd.read_csv(path.joinpath("cluster-labels.csv"), index_col=0, header=None))

        for run_path in sorted(basedir.joinpath(path.joinpath("signatures")).iterdir()):
            n_cluster = run_path.name.split("cl")[1].split(".")[0]
            signature = pd.read_csv(run_path, index_col=0).index.tolist()
            signatures.append(signature)
            sig_index.append([f"iter{i}", n_cluster])
            runs.append(n_run)

    resdict = {
        "signatures": signatures,
        "integration_runs": integration_runs,
        "runs": runs,
        "sig_index": sig_index,
        "cluster_memb": cluster_memb,
    }
    return resdict


def save_metasignatures(meta_signatures: Dict[str, np.ndarray], res_dir: pl.Path) -> None:
    """Saves the metasignatures

    Args:
        meta_signatures: a dict containing the results of the metasignatures found
        res_dir: path to the directory in which to save the metasignatures

    Returns:
        None

    See Also:
        `get_metasignatures`, function used to compute metasignatures
    """
    for cluster in meta_signatures:
        name = f"{cluster}.csv"
        pd.DataFrame(meta_signatures[cluster]).to_csv(res_dir / name)


def save_cell_metamembership(metamembership: pd.DataFrame, prob_metamembership: pd.DataFrame, res_dir: pl.Path) -> None:
    """Saves the metamembership and probability of metamembership

    Args:
        metamembership: assigned metamemberships per cell
        prob_metamembership: probability of having a metamembership per cell
        res_dir: path to the directory to save

    Returns:
        None

    See Also:
        `get_cell_metamembership`, function used to compute metasignatures
    """
    metamembership.to_csv(res_dir / "cell-metamembership.csv")
    prob_metamembership.to_csv(res_dir / "prob-cell-metamembership.csv")


def score_sig(adata: ad.AnnData, signature: Union[np.ndarray, List[str]], score_name: str):
    adata.layers["counts"] = adata.X.copy()
    sc.pp.normalize_total(adata, target_sum=10000)
    sc.pp.log1p(adata)
    sc.tl.score_genes(adata, gene_list=signature, score_name=score_name)
    adata.X = adata.layers["counts"]
    del adata.uns["log1p"]

    return adata


def rename_metasig(meta_signatures):
    nmeta = {}
    for k, v in meta_signatures.items():
        nmeta[f"metasig{k+1}"] = np.array(v)
    return nmeta


# Plotting


def plot_clustermap(
    results: np.ndarray, resdir: pl.Path, filename: str = "clustermap-metasignatures-correlation.png"
) -> None:

    g = sns.clustermap(results, cmap="vlag", center=0)
    g.savefig(resdir / filename, bbox_inches="tight")


def plot_heatmap(
    sim: np.ndarray, idx: np.ndarray, resdir: pl.Path, filename: str = "heatmap-metasignatures.png"
) -> None:
    fig, ax = plt.subplots(figsize=(10, 10))
    sns.heatmap(sim[np.ix_(idx, idx)], ax=ax, cmap="vlag", center=0)
    plt.tick_params(
        axis="both",
        which="both",
        bottom=False,
        left=False,
        labelbottom=False,
        labelleft=False,
    )
    fig.savefig(resdir / filename, bbox_inches="tight")


def viz_clusters_runs(
    sim: np.ndarray,
    clusters: np.ndarray,
    runs: List[int],
    resdir: pl.Path,
    min_dist: float = 1,
    spread: float = 1.5,
    filename: str = "viz-clusters-runs.png",
) -> None:

    reduce_umap = umap.UMAP(min_dist=min_dist, spread=spread, metric="precomputed")
    reduce_mds = MDS(n_components=2, dissimilarity="precomputed")

    dist = 1 - sim
    embedding_UMAP = reduce_umap.fit_transform(dist)
    embedding_MDS = reduce_mds.fit_transform(dist)

    mds_df = pd.DataFrame(embedding_MDS)
    mds_df = pd.concat([mds_df, pd.Series(clusters).astype("category")], axis=1)
    mds_df = pd.concat([mds_df, pd.Series(runs).astype("category")], axis=1)
    mds_df.columns = ["MDS1", "MDS2", "cluster", "runs"]

    umap_df = pd.DataFrame(embedding_UMAP)
    umap_df = pd.concat([umap_df, pd.Series(clusters).astype("category")], axis=1)
    umap_df = pd.concat([umap_df, pd.Series(runs).astype("category")], axis=1)
    umap_df.columns = ["UMAP1", "UMAP2", "cluster", "runs"]

    fig, ax = plt.subplots(2, 2, figsize=(20, 10))
    flatax = ax.flatten()

    sns.scatterplot(data=umap_df, x="UMAP1", y="UMAP2", hue="cluster", ax=flatax[0])
    flatax[0].legend(loc="center right", bbox_to_anchor=(1.1, 0.5), ncol=1, frameon=False)
    flatax[0].set_title("UMAP clusters")
    sns.scatterplot(data=umap_df, x="UMAP1", y="UMAP2", hue="runs", ax=flatax[2])
    flatax[2].legend(loc="center right", bbox_to_anchor=(1.1, 0.5), ncol=1, frameon=False)
    flatax[2].set_title("UMAP runs")
    sns.scatterplot(data=mds_df, x="MDS1", y="MDS2", hue="cluster", ax=flatax[1])
    flatax[1].legend(loc="center right", bbox_to_anchor=(1.1, 0.5), ncol=1, frameon=False)
    flatax[1].set_title("MDS clusters")
    sns.scatterplot(data=mds_df, x="MDS1", y="MDS2", hue="runs", ax=flatax[3])
    flatax[3].legend(loc="center right", bbox_to_anchor=(1.1, 0.5), ncol=1, frameon=False)
    flatax[3].set_title("MDS runs")

    for ax in flatax:
        ax.spines.right.set_visible(False)
        ax.spines.top.set_visible(False)

    fig.savefig(resdir / filename, bbox_inches="tight")


def plot_metamembership(
    adata: ad.AnnData,
    metamembership: pd.DataFrame,
    prob_metamembership: pd.DataFrame,
    integration_path: pl.Path,
    resdir: pl.Path,
) -> None:

    latent_representations = pd.read_csv(integration_path / "latent-representations.csv", index_col=0, header=None)

    adata_copy = adata.copy()
    adata_copy = adata_copy[prob_metamembership.index, :].copy()
    adata_copy.obs = pd.concat([adata_copy.obs, prob_metamembership], axis=1, join="inner")
    adata_copy.obs = pd.concat([adata_copy.obs, metamembership.astype("category")], axis=1, join="inner")

    plotting_config = plotting.ScatterPlotConfig(
        dim_reduction="both",
        signature_columns=["metamembership"] + [f"metasig{cl+1}" for cl in range(prob_metamembership.shape[1])],
        batch_column="sample_id",
        ncols=2,
    )

    scatter = plotting.ScatterPlot(plotting_config)
    fig = scatter.plot_scatter(adata=adata_copy, representations=latent_representations)
    fig.savefig(resdir / "umap-metamembership.png", bbox_inches="tight")

    del adata_copy


def plot_score_UMAP(
    adata: ad.AnnData,
    meta_signatures: Dict[str, np.ndarray],
    resdir: pl.Path,
    len_sig: int = 1000,
    filename: str = "score-space-UMAP.png",
) -> None:

    sigs_cansig = {}
    for k, v in meta_signatures.items():
        sigs_cansig[k] = v[: min(len_sig, len(v))]

    for sig in sigs_cansig:
        adata = score_sig(adata=adata, signature=sigs_cansig[sig], score_name=sig)

    X_scores = adata.obs[list(sigs_cansig.keys())].values
    adata.obsm["X_scores"] = X_scores

    sc.pp.neighbors(adata, use_rep="X_scores")
    sc.tl.umap(adata)

    fig = sc.pl.umap(adata, color=list(sigs_cansig.keys()), ncols=3, return_fig=True)
    fig.savefig(resdir / filename, bbox_inches="tight")

    adata.obs.drop(list(sigs_cansig.keys()), axis=1, inplace=True)
    del adata.obsm["X_scores"]
