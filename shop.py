"""미니 프로젝트 — 쇼핑몰 장바구니 & 할인 쿠폰

클래스 구성
- Product          : 상품 (클래스 변수로 번호 자동 부여, 재고는 메서드로만 변경)
- Discount         : 쿠폰 부모 클래스 (할인 0원)
  - RateDiscount   : 비율 할인 (최대 할인 금액 제한)
  - FixedDiscount  : 정액 할인 (최소 구매 금액 조건)
- CartItem         : 장바구니에 담긴 상품 1줄 (Product 객체를 속성으로 가짐 — 조합)
- Cart             : 장바구니 (CartItem 목록 + 적용한 쿠폰을 가짐 — 조합)
- Shop             : 상품 목록 · 쿠폰 목록 · 장바구니를 묶어 메뉴를 실행
"""

import unicodedata

LINE_WIDTH = 40
FREE_SHIPPING_THRESHOLD = 30_000
SHIPPING_FEE = 3_000


# ──────────────────────────── 출력 도우미 ────────────────────────────
def display_width(text):
    """한글처럼 폭이 넓은 문자는 2칸으로 계산한 화면 폭"""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def ljust(text, width):
    return text + " " * max(0, width - display_width(text))


def rjust(text, width):
    return " " * max(0, width - display_width(text)) + text


def won(amount):
    return f"{amount:,}원"


# ──────────────────────────── 상품 ────────────────────────────
class Product:
    _next_id = 1  # 클래스 변수: 객체가 만들어질 때마다 1씩 증가

    def __init__(self, name, price, stock):
        self.__id = Product._next_id
        Product._next_id += 1
        self.__name = name
        self.__price = price
        self.__stock = stock

    # 읽기 전용 속성 (외부에서 직접 수정 불가)
    @property
    def id(self):
        return self.__id

    @property
    def name(self):
        return self.__name

    @property
    def price(self):
        return self.__price

    @property
    def stock(self):
        return self.__stock

    def is_sold_out(self):
        return self.__stock == 0

    def decrease_stock(self, quantity):
        """재고 변경은 이 메서드로만 한다"""
        if quantity <= 0:
            raise ValueError("감소 수량은 1 이상이어야 합니다.")
        if quantity > self.__stock:
            raise ValueError("재고보다 많이 줄일 수 없습니다.")
        self.__stock -= quantity

    def __str__(self):
        stock_text = "품절" if self.is_sold_out() else f"재고 {self.__stock}개"
        return f"{self.__id}. {ljust(self.__name, 12)}{rjust(won(self.__price), 9)}  ({stock_text})"


# ──────────────────────────── 쿠폰 ────────────────────────────
class Discount:
    """쿠폰 없음 — 모든 쿠폰의 공통 틀"""

    @property
    def name(self):
        return "쿠폰 없음"

    def discount_amount(self, total):
        return 0

    def __str__(self):
        return self.name


class RateDiscount(Discount):
    def __init__(self, rate, max_amount):
        self.__rate = rate
        self.__max_amount = max_amount

    @property
    def name(self):
        return f"{round(self.__rate * 100)}% 할인 (최대 {self.__max_amount:,}원)"

    def discount_amount(self, total):
        # 원 단위 미만 버림 (부동소수 오차 보정용 1e-9)
        amount = int(total * self.__rate + 1e-9)
        return min(amount, self.__max_amount)


class FixedDiscount(Discount):
    def __init__(self, amount, min_total):
        self.__amount = amount
        self.__min_total = min_total

    @property
    def name(self):
        return f"{self.__amount:,}원 할인 ({self.__min_total:,}원 이상 구매 시)"

    def discount_amount(self, total):
        return self.__amount if total >= self.__min_total else 0


# ──────────────────────────── 장바구니 ────────────────────────────
class CartItem:
    def __init__(self, product, quantity):
        self.__product = product  # 조합: Product 객체를 속성으로 가짐
        self.__quantity = quantity

    @property
    def product(self):
        return self.__product

    @property
    def quantity(self):
        return self.__quantity

    def add_quantity(self, quantity):
        self.__quantity += quantity

    def subtotal(self):
        return self.__product.price * self.__quantity

    def __str__(self):
        return f"{ljust(self.__product.name, 12)}x {self.__quantity:<3}{rjust(won(self.subtotal()), 12)}"


class Cart:
    def __init__(self):
        self.__items = {}  # 상품 번호 → CartItem
        self.__coupon = Discount()

    @property
    def coupon(self):
        return self.__coupon

    def is_empty(self):
        return not self.__items

    def quantity_of(self, product):
        item = self.__items.get(product.id)
        return item.quantity if item else 0

    def add(self, product, quantity):
        """담기. 실패하면 ValueError(안내 문구)를 던진다."""
        if product.is_sold_out():
            raise ValueError("품절된 상품입니다.")
        if quantity <= 0:
            raise ValueError("수량은 1개 이상이어야 합니다.")
        available = product.stock - self.quantity_of(product)
        if quantity > available:
            raise ValueError(f"재고가 부족합니다. (담을 수 있는 수량: {available}개)")

        if product.id in self.__items:
            self.__items[product.id].add_quantity(quantity)
        else:
            self.__items[product.id] = CartItem(product, quantity)

    def remove(self, product):
        if product.id not in self.__items:
            raise ValueError("장바구니에 없는 상품입니다.")
        del self.__items[product.id]

    def apply_coupon(self, coupon):
        self.__coupon = coupon

    # ── 금액 계산 ──
    def total(self):
        return sum(item.subtotal() for item in self.__items.values())

    def discount(self):
        # 다형성: 쿠폰 종류와 상관없이 같은 메서드를 호출한다
        return self.__coupon.discount_amount(self.total())

    def shipping_fee(self):
        if self.is_empty():
            return 0
        return 0 if self.total() - self.discount() >= FREE_SHIPPING_THRESHOLD else SHIPPING_FEE

    def payment(self):
        return self.total() - self.discount() + self.shipping_fee()

    # ── 결제 ──
    def checkout(self):
        """재고 감소 → 장바구니 비우기 → 쿠폰 초기화"""
        for item in self.__items.values():
            item.product.decrease_stock(item.quantity)
        self.__items.clear()
        self.__coupon = Discount()

    def summary(self):
        line = "-" * LINE_WIDTH
        discount = self.discount()
        discount_text = won(-discount) if discount else won(0)
        rows = [line]
        rows += [str(item) for item in self.__items.values()]
        rows += [
            line,
            f"{ljust('상품 합계', 16)}{rjust(won(self.total()), 13)}",
            f"{ljust('할인', 16)}{rjust(discount_text, 13)}  [{self.__coupon.name}]",
            f"{ljust('배송비', 16)}{rjust(won(self.shipping_fee()), 13)}",
            f"{ljust('결제 금액', 16)}{rjust(won(self.payment()), 13)}",
            line,
        ]
        return "\n".join(rows)


# ──────────────────────────── 쇼핑몰 ────────────────────────────
class Shop:
    MENU = "1.상품목록 2.담기 3.빼기 4.장바구니 5.쿠폰 6.결제 q.종료"

    def __init__(self, products, coupons):
        self.__products = {p.id: p for p in products}
        self.__coupons = coupons
        self.__cart = Cart()

    # ── 입력 도우미 ──
    @staticmethod
    def _input_int(prompt):
        text = input(prompt).strip()
        if not text.lstrip("-").isdigit():
            raise ValueError("숫자를 입력해 주세요.")
        return int(text)

    def _input_product(self):
        product = self.__products.get(self._input_int("상품 번호: "))
        if product is None:
            raise ValueError("없는 상품 번호입니다.")
        return product

    # ── 메뉴 동작 ──
    def show_products(self):
        for product in self.__products.values():
            print(product)

    def add_to_cart(self):
        product = self._input_product()
        if product.is_sold_out():  # 품절이면 수량을 묻지 않는다
            raise ValueError("품절된 상품입니다.")
        quantity = self._input_int("수량: ")
        self.__cart.add(product, quantity)
        print(f"{product.name} {quantity}개를 담았습니다.")

    def remove_from_cart(self):
        if self.__cart.is_empty():
            raise ValueError("장바구니가 비어 있습니다.")
        product = self._input_product()
        self.__cart.remove(product)
        print(f"{product.name}을(를) 장바구니에서 뺐습니다.")

    def show_cart(self):
        if self.__cart.is_empty():
            print("장바구니가 비어 있습니다.")
            return
        print(self.__cart.summary())

    def choose_coupon(self):
        for i, coupon in enumerate(self.__coupons, start=1):
            print(f"{i}. {coupon}")
        number = self._input_int("쿠폰 번호: ")
        if not 1 <= number <= len(self.__coupons):
            raise ValueError("없는 쿠폰 번호입니다.")
        coupon = self.__coupons[number - 1]
        self.__cart.apply_coupon(coupon)
        print(f"[{coupon}] 쿠폰을 적용했습니다.")

    def checkout(self):
        if self.__cart.is_empty():
            raise ValueError("장바구니가 비어 있습니다.")
        print("=" * 15 + " 영  수  증 " + "=" * 15)
        print(self.__cart.summary())
        self.__cart.checkout()
        print("결제가 완료되었습니다. 감사합니다!")

    def run(self):
        actions = {
            "1": self.show_products,
            "2": self.add_to_cart,
            "3": self.remove_from_cart,
            "4": self.show_cart,
            "5": self.choose_coupon,
            "6": self.checkout,
        }
        while True:
            print("-" * 46)
            print(self.MENU)
            print("-" * 46)
            try:
                choice = input("선택: ").strip().lower()
            except EOFError:
                print()
                break
            if choice == "q":
                print("이용해 주셔서 감사합니다.")
                break
            action = actions.get(choice)
            if action is None:
                print("메뉴에 있는 번호를 입력해 주세요.")
                continue
            try:
                action()
            except ValueError as e:
                print(e)
            except EOFError:
                print()
                break
            print()


def main():
    products = [
        Product("무선 이어폰", 89_000, 3),
        Product("텀블러", 15_000, 10),
        Product("보조배터리", 32_000, 5),
        Product("마우스패드", 9_000, 0),
        Product("USB 허브", 18_000, 4),
    ]
    coupons = [
        Discount(),
        RateDiscount(rate=0.1, max_amount=5000),
        FixedDiscount(amount=3000, min_total=20000),
    ]
    Shop(products, coupons).run()


if __name__ == "__main__":
    main()