import 'package:material_ui/material_ui.dart';

import '../l10n.dart';
import '../theme.dart';
import '../widgets/common.dart';
import '../widgets/language_button.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _busy = false;
  String? _problem;

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() {
      _busy = true;
      _problem = null;
    });
    final session = context.session;
    final messenger = ScaffoldMessenger.of(context);
    final created = context.t('accountCreated');
    try {
      await session.register(name: _name.text, email: _email.text, password: _password.text);
      messenger.showSnackBar(SnackBar(content: Text(created), behavior: SnackBarBehavior.floating, duration: const Duration(seconds: 6)));
      if (mounted) Navigator.of(context).pop(true);
    } on Object catch (error) {
      if (mounted) setState(() => _problem = context.errorText(error));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(context.t('createAccount')), actions: const [LanguageButton()]),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Form(
            key: _form,
            child: AutofillGroup(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(context.t('createAccountLead'), style: const TextStyle(fontSize: 17, color: AppColors.inkSoft)),
                  const SizedBox(height: 20),
                  TextFormField(
                    controller: _name,
                    decoration: InputDecoration(labelText: context.t('fullName')),
                    textCapitalization: TextCapitalization.words,
                    autofillHints: const [AutofillHints.name],
                    textInputAction: TextInputAction.next,
                    validator: (value) => validateRequired(context, value),
                  ),
                  const SizedBox(height: 14),
                  TextFormField(
                    controller: _email,
                    decoration: InputDecoration(labelText: context.t('email')),
                    keyboardType: TextInputType.emailAddress,
                    autocorrect: false,
                    autofillHints: const [AutofillHints.email],
                    textInputAction: TextInputAction.next,
                    validator: (value) => validateEmail(context, value),
                  ),
                  const SizedBox(height: 14),
                  TextFormField(
                    controller: _password,
                    decoration: InputDecoration(labelText: context.t('password'), helperText: context.t('passwordHint')),
                    obscureText: true,
                    autofillHints: const [AutofillHints.newPassword],
                    onFieldSubmitted: (_) => _submit(),
                    validator: (value) => (value == null || value.length < 8) ? context.t('passwordShort') : null,
                  ),
                  if (_problem != null) ...[const SizedBox(height: 16), ProblemText(_problem!)],
                  const SizedBox(height: 24),
                  FilledButton(onPressed: _busy ? null : _submit, child: _busy ? buttonSpinner : Text(context.t('createAccount'))),
                  const SizedBox(height: 8),
                  TextButton(onPressed: _busy ? null : () => Navigator.of(context).pop(false), child: Text(context.t('haveAccount'))),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

String? validateRequired(BuildContext context, String? value) => (value == null || value.trim().isEmpty) ? context.t('fieldRequired') : null;

String? validateEmail(BuildContext context, String? value) {
  final text = value?.trim() ?? '';
  if (text.isEmpty) return context.t('fieldRequired');
  return RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(text) ? null : context.t('emailInvalid');
}
