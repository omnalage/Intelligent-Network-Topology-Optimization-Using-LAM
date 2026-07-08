from main import setup_network
from ai_network_recommender import collect_network_metrics, equal_weight_select_and_train

routers, pubs, subs = setup_network()   # returns your Router objects
csv_path = collect_network_metrics(routers, n_iterations=100, perturb=True, out_csv="Path_Iterations/network_metrics.csv")
res = equal_weight_select_and_train(csv_path, selection_out="Path_Iterations/network_selection_history.csv", min_iters_for_training=8)
print(res['selection_df'].head())
