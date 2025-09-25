import 'dart:math';

double _toDouble(dynamic x) {
  if (x is num) return x.toDouble();
  if (x is String) return double.tryParse(x) ?? 0.0;
  return 0.0;
}

class Obstacle {
  final double distanceM;
  final double angleDeg;

  Obstacle({required this.distanceM, required this.angleDeg});

  factory Obstacle.fromJson(Map<String, dynamic> j) => Obstacle(
        distanceM: _toDouble(j['distance']),
        angleDeg: _toDouble(j['angle']),
      );
}

class SensorData {
  /// 來自後端 data.offset
  final double offsetDeg;

  /// 從 obstacles 中挑的代表距離（預設取「最近」）
  final double? mainDistanceM;

  /// 全部障礙物（可用於進階 UI）
  final List<Obstacle> obstacles;

  /// 後端 warnings 轉成 List<String>
  final List<String> warnings;

  SensorData({
    required this.offsetDeg,
    required this.mainDistanceM,
    required this.obstacles,
    required this.warnings,
  });

  /// 直接吃「後端整包 JSON」：
  /// {
  ///   "timestamp": "...",
  ///   "status": "success",
  ///   "data": { "offset": ..., "obstacles": [...], "warnings": [...] }
  /// }
  factory SensorData.fromTopLevelJson(Map<String, dynamic> j) {
    final data = (j['data'] as Map?) ?? {};
    final obsList = <Obstacle>[];
    final rawObs = data['obstacles'];

    if (rawObs is List) {
      for (final e in rawObs) {
        if (e is Map) obsList.add(Obstacle.fromJson(e.cast<String, dynamic>()));
      }
    }

    // 代表距離：選最近的一個（沒有就 null）
    final mainDist = obsList.isEmpty
        ? null
        : obsList.map((o) => o.distanceM).reduce(min);

    final rawWarn = data['warnings'];
    final warns = (rawWarn is List)
        ? rawWarn.whereType<String>().toList()
        : <String>[];

    return SensorData(
      offsetDeg: _toDouble(data['offset']),
      mainDistanceM: mainDist,
      obstacles: obsList,
      warnings: warns,
    );
  }
}
