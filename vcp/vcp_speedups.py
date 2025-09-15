from scipy.signal import find_peaks


def fast_find_contractions(prices, min_distance=5):
    peaks, _ = find_peaks(prices, distance=min_distance)
    troughs, _ = find_peaks(-prices, distance=min_distance)
    return peaks, troughs

