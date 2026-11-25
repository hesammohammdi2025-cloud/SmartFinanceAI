import pandas as pd
from sklearn.linear_model import LinearRegression


def predict_next_month(monthly_expenses):
    """
    پیش‌بینی هزینه ماه آینده با استفاده از هزینه‌های ماهانه گذشته.
    حداقل به 3 ماه داده برای شروع نیاز داریم.
    """

    if len(monthly_expenses) < 3:
        return {
            'success': False,
            'message': 'برای پیش‌بینی، حداقل ۳ ماه داده ماهانه لازم است.',
            'predicted_expense': None,
        }

    if all(value == 0 for value in monthly_expenses):
        return {
            'success': False,
            'message': 'هزینه ثبت‌شده‌ای برای آموزش مدل وجود ندارد.',
            'predicted_expense': None,
        }

    df = pd.DataFrame({
        'month': range(1, len(monthly_expenses) + 1),
        'expense': monthly_expenses,
    })

    X = df[['month']]
    y = df['expense']

    model = LinearRegression()
    model.fit(X, y)

    next_month = [[len(monthly_expenses) + 1]]
    prediction = model.predict(next_month)[0]

    # هزینه منفی معنا ندارد
    prediction = max(0, float(prediction))

    return {
        'success': True,
        'message': 'پیش‌بینی با موفقیت انجام شد.',
        'predicted_expense': round(prediction, 2),
    }