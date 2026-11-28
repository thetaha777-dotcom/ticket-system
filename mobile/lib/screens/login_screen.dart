import 'package:material_ui/material_ui.dart';

import '../l10n.dart';
import '../theme.dart';
import '../widgets/brand_logo.dart';
import '../widgets/common.dart';
import '../widgets/language_button.dart';
import 'register_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _form = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _server = TextEditingController();
  bool _busy = false;
  bool _serverFilled = false;
  String? _problem;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_serverFilled) {
      _server.text = context.session.serverUrl;
      _serverFilled = true;
    }
  }

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    _server.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() {
      _busy = true;
      _problem = null;
    });
    final session = context.session;
    try {
      await session.signIn(_email.text, _password.text, serverUrl: _server.text);
      if (mounted) Navigator.of(context).pop(true);
    } on Object catch (error) {
      if (mounted) setState(() => _problem = context.errorText(error));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _openRegister() async {
    final session = context.session;
    await session.setServerUrl(_server.text);
    if (!mounted) return;
    final created = await Navigator.of(context).push<bool>(MaterialPageRoute(builder: (_) => const RegisterScreen()));
    if ((created ?? false) && mounted) Navigator.of(context).pop(true);
  }

  String? _required(String? value) => (value == null || value.trim().isEmpty) ? context.t('required') : null;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(context.t('appTitle')), actions: const [LanguageButton()]),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Form(
            key: _form,
            child: AutofillGroup(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Align(alignment: Alignment.centerLeft, child: BrandLogo(height: 48)),
                  const SizedBox(height: 20),
                  Text(context.t('signInTitle'), style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w700, color: AppColors.ink)),
                  const SizedBox(height: 8),
                  Text(context.t('signInLead'), style: const TextStyle(fontSize: 16, color: AppColors.inkSoft)),
                  const SizedBox(height: 24),
                  TextFormField(
                    controller: _email,
                    decoration: InputDecoration(labelText: context.t('email')),
                    keyboardType: TextInputType.emailAddress,
                    autofillHints: const [AutofillHints.username],
                    textInputAction: TextInputAction.next,
                    validator: _required,
                  ),
                  const SizedBox(height: 14),
                  TextFormField(
                    controller: _password,
                    decoration: InputDecoration(labelText: context.t('password')),
                    obscureText: true,
                    autofillHints: const [AutofillHints.password],
                    onFieldSubmitted: (_) => _submit(),
                    validator: _required,
                  ),
                  const SizedBox(height: 14),
                  TextFormField(
                    controller: _server,
                    decoration: InputDecoration(labelText: context.t('server'), helperText: context.t('serverHint'), helperMaxLines: 2),
                    keyboardType: TextInputType.url,
                    autocorrect: false,
                    validator: _required,
                  ),
                  if (_problem != null) ...[
                    const SizedBox(height: 16),
                    Semantics(
                      liveRegion: true,
                      child: Text(_problem!, style: const TextStyle(color: AppColors.bad, fontSize: 16, fontWeight: FontWeight.w600)),
                    ),
                  ],
                  const SizedBox(height: 24),
                  FilledButton(
                    onPressed: _busy ? null : _submit,
                    child: _busy
                        ? buttonSpinner
                        : Text(context.t('signIn')),
                  ),
                  const Divider(height: 32),
                  Text(context.t('createAccountLead'), textAlign: TextAlign.center, style: const TextStyle(color: AppColors.inkSoft, fontSize: 15)),
                  const SizedBox(height: 10),
                  OutlinedButton(onPressed: _busy ? null : _openRegister, child: Text(context.t('noAccount'))),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
