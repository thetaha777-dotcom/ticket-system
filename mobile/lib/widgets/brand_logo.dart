import 'package:flutter_svg/flutter_svg.dart';
import 'package:material_ui/material_ui.dart';

import '../theme.dart';

/// The BiletFlow wordmark: the ticket logo (which says "Bilet") followed by "Flow", as on the website.
/// Screen readers hear one word, "BiletFlow".
class BrandLogo extends StatelessWidget {
  const BrandLogo({super.key, this.height = 34});

  /// Height of the ticket; the text is sized to match.
  final double height;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'BiletFlow',
      excludeSemantics: true,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          SvgPicture.asset('assets/logo.svg', height: height),
          SizedBox(width: height * 0.15),
          Text(
            'Flow',
            style: TextStyle(fontSize: height * 0.7, fontWeight: FontWeight.w800, color: AppColors.skyDeep, letterSpacing: 0.3, height: 1),
          ),
        ],
      ),
    );
  }
}
