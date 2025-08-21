"""
이메일 서비스
실제 이메일 발송을 위한 유틸리티
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from typing import Optional
import os

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailService:
    def __init__(self):
        # SendGrid 설정 (우선순위)
        self.sendgrid_api_key = settings.sendgrid_api_key
        self.sendgrid_from_email = settings.sendgrid_from_email
        
        # 기존 SMTP 설정 (fallback)
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password

    async def send_verification_email(self, to_email: str, verification_code: str) -> bool:
        """
        이메일 인증 코드 발송
        
        Args:
            to_email: 수신자 이메일
            verification_code: 인증 코드
            
        Returns:
            발송 성공 여부
        """
        try:
            # SendGrid API 키가 있으면 SendGrid 사용
            if self.sendgrid_api_key:
                return await self._send_with_sendgrid(to_email, verification_code)
            else:
                # 기존 SMTP 방식 사용 (fallback)
                return await self._send_with_smtp(to_email, verification_code)
                
        except Exception as e:
            logger.error(f"Verification email sending failed: {to_email} - {e}")
            return False

    async def _send_with_sendgrid(self, to_email: str, verification_code: str) -> bool:
        """SendGrid를 사용한 이메일 발송"""
        try:
            import httpx
            
            # 디버깅을 위한 로그 추가
            logger.info(f"SendGrid 발신자 이메일: {self.sendgrid_from_email}")
            logger.info(f"수신자 이메일: {to_email}")
            
            # SendGrid API 엔드포인트
            url = "https://api.sendgrid.com/v3/mail/send"
            
            # 이메일 제목과 내용 (임시 영어 버전)
            subject = "[Saegim] Email Verification Code"
            
            html_content = f"""
            <html>
            <body>
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #5C8D89;">Saegim Email Verification</h2>
                    <p>Hello! Thank you for signing up for Saegim service.</p>
                    <p>Please enter the verification code below to complete your email verification.</p>
                    
                    <div style="background-color: #f5f5f5; padding: 20px; text-align: center; margin: 20px 0;">
                        <h3 style="color: #5C8D89; font-size: 24px; letter-spacing: 5px;">{verification_code}</h3>
                    </div>
                    
                    <p><strong>This verification code will expire in 10 minutes.</strong></p>
                    
                    <p>If you did not request this, please ignore this email.</p>
                    
                    <hr style="margin: 30px 0;">
                    <p style="color: #666; font-size: 12px;">
                        This email was sent from Saegim service.<br>
                        If you have any questions, please contact our customer service.
                    </p>
                </div>
            </body>
            </html>
            """
            
            # SendGrid API 요청 데이터
            data = {
                "personalizations": [
                    {
                        "to": [{"email": to_email}]
                    }
                ],
                "from": {"email": self.sendgrid_from_email},
                "subject": subject,
                "content": [
                    {
                        "type": "text/html",
                        "value": html_content
                    }
                ]
            }
            
            # API 요청 헤더
            headers = {
                "Authorization": f"Bearer {self.sendgrid_api_key}",
                "Content-Type": "application/json"
            }
            
            # SendGrid API 호출
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, headers=headers)
            
            if response.status_code == 202:
                logger.info(f"SendGrid verification email sent successfully: {to_email}")
                return True
            else:
                logger.error(f"SendGrid API 오류: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"SendGrid email sending failed: {e}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error args: {e.args}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False

    async def _send_with_smtp(self, to_email: str, verification_code: str) -> bool:
        """기존 SMTP를 사용한 이메일 발송"""
        try:
            # 이메일 제목과 내용
            subject = "[Saegim] Email Verification Code"
            
            html_content = f"""
            <html>
            <body>
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #5C8D89;">Saegim Email Verification</h2>
                    <p>Hello! Thank you for signing up for Saegim service.</p>
                    <p>Please enter the verification code below to complete your email verification.</p>
                    
                    <div style="background-color: #f5f5f5; padding: 20px; text-align: center; margin: 20px 0;">
                        <h3 style="color: #5C8D89; font-size: 24px; letter-spacing: 5px;">{verification_code}</h3>
                    </div>
                    
                    <p><strong>This verification code will expire in 10 minutes.</strong></p>
                    
                    <p>If you did not request this, please ignore this email.</p>
                    
                    <hr style="margin: 30px 0;">
                    <p style="color: #666; font-size: 12px;">
                        This email was sent from Saegim service.<br>
                        If you have any questions, please contact our customer service.
                    </p>
                </div>
            </body>
            </html>
            """
            
            # 이메일 메시지 생성
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            # HTML 내용 추가
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # SMTP 서버 연결 및 이메일 발송
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"SMTP 인증 이메일 발송 성공: {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"SMTP 이메일 발송 실패: {to_email} - {e}")
            return False

    async def send_welcome_email(self, to_email: str, nickname: str) -> bool:
        """
        회원가입 완료 환영 이메일 발송
        
        Args:
            to_email: 수신자 이메일
            nickname: 사용자 닉네임
            
        Returns:
            발송 성공 여부
        """
        try:
            # SendGrid API 키가 있으면 SendGrid 사용
            if self.sendgrid_api_key:
                return await self._send_welcome_with_sendgrid(to_email, nickname)
            else:
                # 기존 SMTP 방식 사용 (fallback)
                return await self._send_welcome_with_smtp(to_email, nickname)
                
        except Exception as e:
            logger.error(f"Welcome email sending failed: {to_email} - {e}")
            return False

    async def _send_welcome_with_sendgrid(self, to_email: str, nickname: str) -> bool:
        """SendGrid를 사용한 환영 이메일 발송"""
        try:
            import httpx
            
            url = "https://api.sendgrid.com/v3/mail/send"
            subject = "[Saegim] Welcome to Saegim!"
            
            html_content = f"""
            <html>
            <body>
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #5C8D89;">Welcome to Saegim!</h2>
                    <p>Hello, <strong>{nickname}</strong>!</p>
                    <p>Your Saegim service registration has been completed successfully.</p>
                    
                    <div style="background-color: #f0f8f7; padding: 20px; margin: 20px 0; border-radius: 10px;">
                        <h3 style="color: #5C8D89;">What you can do with Saegim</h3>
                        <ul>
                            <li>Write emotional diaries with AI</li>
                            <li>Emotion analysis and keyword extraction</li>
                            <li>Monthly emotion report</li>
                            <li>Personalized AI style settings</li>
                        </ul>
                    </div>
                    
                    <p>Start using Saegim now!</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{settings.frontend_url}" 
                           style="background-color: #5C8D89; color: white; padding: 12px 30px; 
                                  text-decoration: none; border-radius: 5px; display: inline-block;">
                            Start Saegim
                        </a>
                    </div>
                    
                    <hr style="margin: 30px 0;">
                    <p style="color: #666; font-size: 12px;">
                        This email was sent from Saegim service.<br>
                        If you have any questions, please contact our customer service.
                    </p>
                </div>
            </body>
            </html>
            """
            
            data = {
                "personalizations": [
                    {
                        "to": [{"email": to_email}]
                    }
                ],
                "from": {"email": self.sendgrid_from_email},
                "subject": subject,
                "content": [
                    {
                        "type": "text/html",
                        "value": html_content
                    }
                ]
            }
            
            headers = {
                "Authorization": f"Bearer {self.sendgrid_api_key}",
                "Content-Type": "application/json"
            }
            
            # SendGrid API 호출
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, headers=headers)
            
            if response.status_code == 202:
                logger.info(f"SendGrid welcome email sent successfully: {to_email}")
                return True
            else:
                logger.error(f"SendGrid API 오류: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"SendGrid welcome email sending failed: {e}")
            return False

    async def _send_welcome_with_smtp(self, to_email: str, nickname: str) -> bool:
        """기존 SMTP를 사용한 환영 이메일 발송"""
        try:
            subject = "[Saegim] Welcome to Saegim!"
            
            html_content = f"""
            <html>
            <body>
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #5C8D89;">Welcome to Saegim!</h2>
                    <p>Hello, <strong>{nickname}</strong>!</p>
                    <p>Your Saegim service registration has been completed successfully.</p>
                    
                    <div style="background-color: #f0f8f7; padding: 20px; margin: 20px 0; border-radius: 10px;">
                        <h3 style="color: #5C8D89;">What you can do with Saegim</h3>
                        <ul>
                            <li>Write emotional diaries with AI</li>
                            <li>Emotion analysis and keyword extraction</li>
                            <li>Monthly emotion report</li>
                            <li>Personalized AI style settings</li>
                        </ul>
                    </div>
                    
                    <p>Start using Saegim now!</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{settings.frontend_url}" 
                           style="background-color: #5C8D89; color: white; padding: 12px 30px; 
                                  text-decoration: none; border-radius: 5px; display: inline-block;">
                            Start Saegim
                        </a>
                    </div>
                    
                    <hr style="margin: 30px 0;">
                    <p style="color: #666; font-size: 12px;">
                        This email was sent from Saegim service.<br>
                        If you have any questions, please contact our customer service.
                    </p>
                </div>
            </body>
            </html>
            """
            
            # 이메일 메시지 생성
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            # HTML 내용 추가
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # SMTP 서버 연결 및 이메일 발송
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"SMTP 환영 이메일 발송 성공: {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"SMTP 환영 이메일 발송 실패: {to_email} - {e}")
            return False
