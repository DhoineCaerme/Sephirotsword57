import json

def calculate_metrics(ground_truth_list, extracted_list):
    """Calculates Precision, Recall, and F1 for lists of strings."""
    gt_set = set(ground_truth_list)
    ext_set = set(extracted_list)
    
    true_positives = len(gt_set.intersection(ext_set))
    false_positives = len(ext_set - gt_set)
    false_negatives = len(gt_set - ext_set)
    
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return precision, recall, f1

def evaluate_extraction(doc_id, ground_truth, extracted):
    print(f"Evaluating Doc ID: {doc_id}")
    
    # Evaluate Ports
    p, r, f1 = calculate_metrics(
        ground_truth.get('required_ports', []), 
        extracted.get('required_ports', [])
    )
    print(f"  Ports -> Precision: {p:.2f}, Recall: {r:.2f}, F1: {f1:.2f}")

    # Evaluate Packages
    p, r, f1 = calculate_metrics(
        ground_truth.get('required_packages', []), 
        extracted.get('required_packages', [])
    )
    print(f"  Packages -> Precision: {p:.2f}, Recall: {r:.2f}, F1: {f1:.2f}")


if __name__ == "__main__":
    dummy_ground_truth = {"required_ports": ["8080", "443"], "required_packages": ["nginx"]}
    dummy_extracted = {"required_ports": ["8080"], "required_packages": ["nginx", "curl"]}
    
    evaluate_extraction("TEST-001", dummy_ground_truth, dummy_extracted)