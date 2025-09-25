import 'dart:async';
import 'package:flutter/material.dart';
import 'sensor_data.dart';
import 'services/data_stream_service.dart';

class DataDisplayPanel extends StatefulWidget {
  /// 二選一：給 wsUrl 連真後端，或 useFake=true 先看 UI
  final String? wsUrl;
  final bool useFake;

  /// 門檻設定
  final double angleWarnDeg; // 偏移角度超過就警示
  final double minDistM; // 太近
  final double maxDistM; // 太遠

  const DataDisplayPanel({
    super.key,
    this.wsUrl,
    this.dataUrl,
    this.useFake = false,
    this.angleWarnDeg = 5.0,
    this.minDistM = 0.8,
    this.maxDistM = 2.0,
  });

  @override
  State<DataDisplayPanel> createState() => _DataDisplayPanelState();
}

class _DataDisplayPanelState extends State<DataDisplayPanel> {
  StreamSubscription<SensorData>? _sub;
  SensorData? _last;
  DataStreamService? _svc;
  FakeDataStreamService? _fake;

  @override
  void initState() {
    super.initState();
    if (widget.useFake) {
      _fake = FakeDataStreamService();
      _sub = _fake!.connect().listen((d) => setState(() => _last = d));
    } else if (widget.wsUrl != null) {
      _svc = DataStreamService(widget.wsUrl!);
      _sub = _svc!.connect().listen((d) => setState(() => _last = d));
    }
  }

  @override
  void dispose() {
    _sub?.cancel();
    _svc?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final d = _last;
    final angleBad = d != null && d.offsetDeg.abs() > widget.angleWarnDeg;
    final tooClose =
        d?.mainDistanceM != null && d!.mainDistanceM! < widget.minDistM;
    final tooFar =
        d?.mainDistanceM != null && d!.mainDistanceM! > widget.maxDistM;
    final hasWarn =
        angleBad || tooClose || tooFar || (d?.warnings.isNotEmpty ?? false);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (hasWarn)
          Card(
            color: Theme.of(context).colorScheme.errorContainer,
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Row(
                children: [
                  const Icon(Icons.warning_amber_rounded),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _composeWarning(d, angleBad, tooClose, tooFar),
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ),
                ],
              ),
            ),
          ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: _metricCard(
                title: '偏移角度',
                value: d == null ? '--' : '${d.offsetDeg.toStringAsFixed(1)}°',
                icon: Icons.navigation,
                danger: angleBad,
                subtitle: '門檻 ±${widget.angleWarnDeg.toStringAsFixed(1)}°',
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _metricCard(
                title: '最近距離',
                value: d?.mainDistanceM == null
                    ? '--'
                    : '${d!.mainDistanceM!.toStringAsFixed(2)} m',
                icon: Icons.straighten,
                danger: tooClose || tooFar,
                subtitle: '允許 ${widget.minDistM}-${widget.maxDistM} m',
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        if (d?.mainDistanceM != null) _distanceBar(d!.mainDistanceM!),
      ],
    );
  }

  String _composeWarning(
    SensorData? d,
    bool angleBad,
    bool tooClose,
    bool tooFar,
  ) {
    final msgs = <String>[];
    if (angleBad) msgs.add('偏移過大（>${widget.angleWarnDeg}°）');
    if (tooClose) msgs.add('距離過近（<${widget.minDistM}m）');
    if (tooFar) msgs.add('距離過遠（>${widget.maxDistM}m）');
    if (d != null && d.warnings.isNotEmpty) msgs.addAll(d.warnings);
    return msgs.isEmpty ? '—' : msgs.join(' ・ ');
  }

  Widget _metricCard({
    required String title,
    required String value,
    required IconData icon,
    required bool danger,
    String? subtitle,
  }) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            Icon(icon, size: 28, color: danger ? Colors.red : null),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(fontSize: 13, color: Colors.grey),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    value,
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: danger ? Colors.red : null,
                    ),
                  ),
                  if (subtitle != null) ...[
                    const SizedBox(height: 4),
                    Text(
                      subtitle,
                      style: const TextStyle(fontSize: 12, color: Colors.grey),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _distanceBar(double distanceM) {
    double norm(double x, double a, double b) =>
        ((x - a) / (b - a)).clamp(0.0, 1.0);
    final p = norm(distanceM, widget.minDistM, widget.maxDistM);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('距離指標', style: TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            LinearProgressIndicator(value: p),
            const SizedBox(height: 6),
            Text(
              '目前：${distanceM.toStringAsFixed(2)} m',
              textAlign: TextAlign.right,
              style: const TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ],
        ),
      ),
    );
  }
}
